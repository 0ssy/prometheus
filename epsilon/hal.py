from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class HardwareInterface(ABC):
    name: str

    @abstractmethod
    def capabilities(self) -> list[str]: ...

    @abstractmethod
    def execute(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class _BasicInterface(HardwareInterface):
    def __init__(self, name: str):
        self.name = name

    def capabilities(self) -> list[str]:
        return ["connect", "read", "write", "diagnose"]

    def execute(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        if capability not in self.capabilities():
            raise ValueError(f"{self.name} does not support {capability}")
        return {"interface": self.name, "capability": capability, "payload": payload}


class HALRegistry:
    def __init__(self):
        self._interfaces: dict[str, HardwareInterface] = {}

    def register_default_interfaces(self) -> None:
        for interface_name in ["usb", "bluetooth", "serial", "network", "virtual"]:
            self._interfaces[interface_name] = _BasicInterface(interface_name)

    def list_interfaces(self) -> list[dict]:
        return [
            {"name": interface.name, "capabilities": interface.capabilities()}
            for interface in self._interfaces.values()
        ]

    def get(self, name: str) -> HardwareInterface:
        interface = self._interfaces.get(name)
        if interface is None:
            raise RuntimeError(f"No such hardware interface: {name}")
        return interface
