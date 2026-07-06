from __future__ import annotations

from typing import Any

from hardware.drivers.base import HardwareDriver
from core.logger import get_logger

logger = get_logger(__name__)


class ADBDriver(HardwareDriver):
    """Simulated ADB (Android Debug Bridge) driver."""

    name = "adb"
    transport = "adb"
    connected = False
    capabilities_list = ["connect", "disconnect", "shell", "push", "pull", "reboot", "sideload"]

    def connect(self) -> dict[str, Any]:
        """Simulate connecting to an ADB device."""
        self.connected = True
        logger.info("ADB device connected")
        return {"status": "connected", "transport": self.transport}

    def disconnect(self) -> dict[str, Any]:
        """Simulate disconnecting from an ADB device."""
        self.connected = False
        logger.info("ADB device disconnected")
        return {"status": "disconnected"}

    def identify(self) -> dict[str, Any]:
        """Return mock Android device information."""
        return {
            "name": self.name,
            "transport": self.transport,
            "android_version": "14",
            "sdk": "34",
            "model": "Pixel Simulator",
            "device": "simulator",
            "product": "sdk_gphone64_x86_64",
            "serial": "adb-1234567890",
        }

    def diagnostics(self) -> dict[str, Any]:
        """Return detailed ADB diagnostics."""
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "adb_version": "1.0.41",
            "authorized": True,
            "tests": {
                "connection": "passed",
                "shell_access": "passed",
                "file_transfer": "passed",
            },
            "status": "ok",
        }
