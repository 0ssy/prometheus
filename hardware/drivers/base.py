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
