from __future__ import annotations

from typing import Any

from hardware.drivers.base import HardwareDriver
from core.logger import get_logger

logger = get_logger(__name__)


class VirtualDriver(HardwareDriver):
    """Simulated virtual device driver.

    Bridges to existing simulated devices and serial devices.
    """

    name = "virtual"
    transport = "virtual"
    connected = False
    capabilities_list = ["connect", "disconnect", "read", "write", "diagnose", "simulate"]

    def __init__(self, wrapped_device: Any | None = None) -> None:
        """Initialize the virtual driver.

        Args:
            wrapped_device: Optional existing device instance to wrap.
        """
        super().__init__()
        self._wrapped_device = wrapped_device

    def connect(self) -> dict[str, Any]:
        """Simulate connecting to a virtual device."""
        self.connected = True
        logger.info("Virtual device connected")
        return {"status": "connected", "transport": self.transport}

    def disconnect(self) -> dict[str, Any]:
        """Simulate disconnecting from a virtual device."""
        self.connected = False
        logger.info("Virtual device disconnected")
        return {"status": "disconnected"}

    def status(self) -> dict[str, Any]:
        """Return current virtual device status."""
        return {"connected": self.connected}

    def identify(self) -> dict[str, Any]:
        """Return mock virtual device information."""
        return {
            "name": self.name,
            "transport": self.transport,
            "type": "simulated",
            "wrapped": self._wrapped_device is not None,
        }

    def diagnostics(self) -> dict[str, Any]:
        """Return detailed virtual device diagnostics."""
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "wrapped_device": self._wrapped_device is not None,
            "tests": {
                "connect": "passed",
                "read": "passed",
                "write": "passed",
                "simulate": "passed",
            },
            "status": "ok",
        }

    def read(self, length: int = 1024) -> bytes:
        return b""

    def write(self, data: bytes) -> int:
        return len(data)

    def simulate(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"driver": self.name, "capability": capability, "simulated": True}

    def verify(self) -> dict[str, Any]:
        return {"driver": self.name, "verified": True}
