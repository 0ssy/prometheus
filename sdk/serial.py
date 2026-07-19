"""Prometheus SDK — Serial communication capability client.

Thin, stable SDK surface over the Serial Hardware API. Applications, plugins,
and automation steps use this instead of reaching into `hardware.serial`.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from hardware.serial import (
    SerialManager,
    SerialCapability,
    SerialPort,
    SerialPermissionPolicy,
    get_serial_manager,
)


class Serial:
    """SDK client for the Serial communication capability."""

    def __init__(self, manager: Optional[SerialManager] = None) -> None:
        self._manager = manager or get_serial_manager()

    @property
    def manager(self) -> SerialManager:
        return self._manager

    def enumerate(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._manager.enumerate()]

    def list(self) -> list[dict[str, Any]]:
        return self._manager.list()

    def get(self, port: str) -> Optional[dict[str, Any]]:
        sp = self._manager.get(port)
        return sp.to_dict() if sp else None

    def ports(self) -> list[SerialPort]:
        return self._manager.enumerate()

    def policy(self) -> SerialPermissionPolicy:
        return self._manager.policy()

    def can_access(
        self,
        capability: str,
        port: str,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        serial: Optional[str] = None,
    ) -> tuple[bool, str]:
        cap = (
            capability
            if isinstance(capability, SerialCapability)
            else SerialCapability(capability)
        )
        return self._manager.can_access(cap, port, vendor_id, product_id, serial)

    def configure(self, port: str, baud_rate: int) -> dict[str, Any]:
        return self._manager.configure(port, baud_rate)

    def connect(self, port: str, baud_rate: int = 115200) -> dict[str, Any]:
        return self._manager.connect(port, baud_rate=baud_rate)

    def disconnect(self, port: str) -> dict[str, Any]:
        return self._manager.disconnect(port)

    def read(self, port: str, length: int = 1024) -> bytes:
        return self._manager.read(port, length=length)

    def write(self, port: str, data: bytes) -> int:
        return self._manager.write(port, data)

    def log(self) -> list[dict[str, Any]]:
        return self._manager.log()

    def allow(
        self,
        port: Optional[str] = None,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        serial: Optional[str] = None,
        capabilities: Optional[set[str]] = None,
    ) -> None:
        caps = (
            frozenset(SerialCapability(c) for c in capabilities)
            if capabilities is not None
            else None
        )
        self._manager.policy().allow(
            port=port, vendor_id=vendor_id, product_id=product_id, serial=serial, capabilities=caps
        )

    def deny(
        self,
        port: Optional[str] = None,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        serial: Optional[str] = None,
        reason: str = "denied by policy",
    ) -> None:
        self._manager.policy().deny(
            port=port, vendor_id=vendor_id, product_id=product_id, serial=serial, reason=reason
        )

    def start_monitor(self, interval: float = 1.0) -> None:
        self._manager.start_monitor(interval=interval)

    def stop_monitor(self) -> None:
        self._manager.stop_monitor()

    def on_change(self, handler: Callable[[str, bool], None]) -> None:
        self._manager.on_change(handler)
