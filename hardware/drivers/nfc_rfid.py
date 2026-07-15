from __future__ import annotations

from typing import Any

from hardware.drivers.base import HardwareDriver
from core.logger import get_logger

logger = get_logger(__name__)


class NFCDriver(HardwareDriver):
    """Simulated NFC transport driver for development and testing."""

    name = "nfc"
    transport = "nfc"
    connected = False
    capabilities_list = ["connect", "disconnect", "read", "write", "poll"]

    def connect(self) -> dict[str, Any]:
        """Simulate connecting to an NFC controller."""
        self.connected = True
        logger.info("NFC controller connected")
        return {"status": "connected", "transport": self.transport}

    def disconnect(self) -> dict[str, Any]:
        """Simulate disconnecting from an NFC controller."""
        self.connected = False
        logger.info("NFC controller disconnected")
        return {"status": "disconnected"}

    def identify(self) -> dict[str, Any]:
        """Return mock NFC device information."""
        return {
            "name": self.name,
            "transport": self.transport,
            "standard": "ISO/IEC 14443",
            "max_data_rate": "424 kbps",
        }

    def health(self) -> dict[str, Any]:
        """Return simulated NFC device health metrics."""
        return {
            "status": "ok",
            "field_strength": "strong",
        }

    def diagnostics(self) -> dict[str, Any]:
        """Return detailed NFC diagnostics."""
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "tests": {
                "polling": "passed",
                "read_write": "passed",
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


class RFIDDriver(HardwareDriver):
    """Simulated RFID transport driver for development and testing."""

    name = "rfid"
    transport = "rfid"
    connected = False
    capabilities_list = ["connect", "disconnect", "read", "write", "poll"]

    def connect(self) -> dict[str, Any]:
        """Simulate connecting to an RFID reader."""
        self.connected = True
        logger.info("RFID reader connected")
        return {"status": "connected", "transport": self.transport}

    def disconnect(self) -> dict[str, Any]:
        """Simulate disconnecting from an RFID reader."""
        self.connected = False
        logger.info("RFID reader disconnected")
        return {"status": "disconnected"}

    def identify(self) -> dict[str, Any]:
        """Return mock RFID device information."""
        return {
            "name": self.name,
            "transport": self.transport,
            "standard": "ISO/IEC 15693",
            "frequency": "13.56 MHz",
        }

    def health(self) -> dict[str, Any]:
        """Return simulated RFID device health metrics."""
        return {
            "status": "ok",
            "antenna_status": "active",
            "signal_strength": "strong",
        }

    def diagnostics(self) -> dict[str, Any]:
        """Return detailed RFID diagnostics."""
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "tests": {
                "polling": "passed",
                "tag_detection": "passed",
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
