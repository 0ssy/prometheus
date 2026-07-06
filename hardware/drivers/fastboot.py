from __future__ import annotations

from typing import Any

from hardware.drivers.base import HardwareDriver
from core.logger import get_logger

logger = get_logger(__name__)


class FastbootDriver(HardwareDriver):
    """Simulated fastboot mode driver."""

    name = "fastboot"
    transport = "usb"
    connected = False
    capabilities_list = ["connect", "disconnect", "flash", "erase", "boot", "getvar"]

    def connect(self) -> dict[str, Any]:
        """Simulate connecting to a fastboot device."""
        self.connected = True
        logger.info("Fastboot device connected")
        return {"status": "connected", "transport": self.transport}

    def disconnect(self) -> dict[str, Any]:
        """Simulate disconnecting from a fastboot device."""
        self.connected = False
        logger.info("Fastboot device disconnected")
        return {"status": "disconnected"}

    def identify(self) -> dict[str, Any]:
        """Return mock fastboot device information."""
        return {
            "name": self.name,
            "transport": self.transport,
            "product": "fastboot_simulator",
            "version": "0.1",
            "serial": "fastboot-abcdef123456",
        }

    def diagnostics(self) -> dict[str, Any]:
        """Return detailed fastboot diagnostics."""
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "fastboot_version": "1.0.0",
            "tests": {
                "enumerate": "passed",
                "flash": "passed",
                "erase": "passed",
                "boot": "passed",
                "getvar": "passed",
            },
            "status": "ok",
        }
