from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from hardware.hal.interface import HardwareInterface
from core.logger import get_logger

logger = get_logger(__name__)


class HardwareDriver(HardwareInterface, ABC):
    """Abstract base class for hardware drivers."""

    name: str
    transport: str
    connected: bool = False
    capabilities_list: list[str] = []
    session_id: str | None = None

    def __init__(self) -> None:
        self.capabilities_list = list(self.__class__.capabilities_list)

    @abstractmethod
    def connect(self) -> dict[str, Any]:
        """Establish connection to the hardware device."""
        ...

    @abstractmethod
    def disconnect(self) -> dict[str, Any]:
        """Terminate connection to the hardware device."""
        ...

    def identify(self) -> dict[str, Any]:
        """Return identifying information about the hardware device."""
        return {"name": self.name, "transport": self.transport}

    def capabilities(self) -> list[str]:
        """Return a list of supported capabilities."""
        return list(self.capabilities_list)

    def execute(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute a specific capability with the given payload."""
        if capability not in self.capabilities_list:
            raise ValueError(f"{self.name} does not support capability: {capability}")
        return {"driver": self.name, "capability": capability, "payload": payload}

    def health(self) -> dict[str, Any]:
        """Return health metrics for the connected device."""
        return {"status": "unknown", "details": {}}

    def diagnostics(self) -> dict[str, Any]:
        """Run diagnostics on the connected device."""
        return {"driver": self.name, "status": "ok", "results": {}}

    def read(self, length: int = 1024) -> bytes:
        """Read data from the device."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support read")

    def write(self, data: bytes) -> int:
        """Write data to the device."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support write")

    def simulate(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Simulate a capability execution without side effects."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support simulate")

    def verify(self) -> dict[str, Any]:
        """Verify device integrity and authenticity."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support verify")

    def backup(self) -> dict[str, Any]:
        """Backup device state."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support backup")

    def restore(self, backup_data: dict[str, Any]) -> dict[str, Any]:
        """Restore device state from backup."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support restore")

    def factory_reset(self) -> dict[str, Any]:
        """Perform factory reset on the device."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support factory_reset")
