from __future__ import annotations

from typing import Any

from hardware.drivers.base import HardwareDriver
from core.logger import get_logger

logger = get_logger(__name__)


class PCIeDriver(HardwareDriver):
    """Simulated PCIe driver for development and testing."""

    name = "pcie"
    transport = "pcie"
    connected = False
    capabilities_list = ["connect", "disconnect", "read", "write", "diagnose"]

    def connect(self) -> dict[str, Any]:
        self.connected = True
        logger.info("PCIe device connected")
        return {"status": "connected", "transport": self.transport}

    def disconnect(self) -> dict[str, Any]:
        self.connected = False
        logger.info("PCIe device disconnected")
        return {"status": "disconnected"}

    def identify(self) -> dict[str, Any]:
        return {"name": self.name, "transport": self.transport, "vendor_id": "0x8086", "device_id": "0x1234"}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "link_speed": "16GT/s", "link_width": "x16"}

    def diagnostics(self) -> dict[str, Any]:
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "tests": {"link_training": "passed", "memory_test": "passed"},
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


class SATADriver(HardwareDriver):
    """Simulated SATA driver for development and testing."""

    name = "sata"
    transport = "sata"
    connected = False
    capabilities_list = ["connect", "disconnect", "read", "write", "diagnose"]

    def connect(self) -> dict[str, Any]:
        self.connected = True
        logger.info("SATA device connected")
        return {"status": "connected", "transport": self.transport}

    def disconnect(self) -> dict[str, Any]:
        self.connected = False
        logger.info("SATA device disconnected")
        return {"status": "disconnected"}

    def identify(self) -> dict[str, Any]:
        return {"name": self.name, "transport": self.transport, "vendor_id": "0x15AD", "device_id": "0x07C0"}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "interface_speed": "6Gb/s", "transfer_mode": "UASP"}

    def diagnostics(self) -> dict[str, Any]:
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "tests": {"link_established": "passed", "data_integrity": "passed"},
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


class NVMeDriver(HardwareDriver):
    """Simulated NVMe driver for development and testing."""

    name = "nvme"
    transport = "pcie"
    connected = False
    capabilities_list = ["connect", "disconnect", "read", "write", "diagnose"]

    def connect(self) -> dict[str, Any]:
        self.connected = True
        logger.info("NVMe device connected")
        return {"status": "connected", "transport": self.transport}

    def disconnect(self) -> dict[str, Any]:
        self.connected = False
        logger.info("NVMe device disconnected")
        return {"status": "disconnected"}

    def identify(self) -> dict[str, Any]:
        return {"name": self.name, "transport": self.transport, "vendor_id": "0x144D", "device_id": "0xA808"}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "pcie_lanes": "x4", "form_factor": "M.2"}

    def diagnostics(self) -> dict[str, Any]:
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "tests": {"controller_status": "passed", "namespace_readiness": "passed"},
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


class SDDriver(HardwareDriver):
    """Simulated SD driver for development and testing."""

    name = "sd"
    transport = "sd"
    connected = False
    capabilities_list = ["connect", "disconnect", "read", "write", "diagnose"]

    def connect(self) -> dict[str, Any]:
        self.connected = True
        logger.info("SD device connected")
        return {"status": "connected", "transport": self.transport}

    def disconnect(self) -> dict[str, Any]:
        self.connected = False
        logger.info("SD device disconnected")
        return {"status": "disconnected"}

    def identify(self) -> dict[str, Any]:
        return {"name": self.name, "transport": self.transport, "vendor_id": "0x0000", "device_id": "0x0000"}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "card_type": "SDXC", "speed_class": "UHS-I"}

    def diagnostics(self) -> dict[str, Any]:
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "tests": {"card_detected": "passed", "file_system_check": "passed"},
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


class MicroSDDriver(HardwareDriver):
    """Simulated microSD driver for development and testing."""

    name = "microsd"
    transport = "microsd"
    connected = False
    capabilities_list = ["connect", "disconnect", "read", "write", "diagnose"]

    def connect(self) -> dict[str, Any]:
        self.connected = True
        logger.info("MicroSD device connected")
        return {"status": "connected", "transport": self.transport}

    def disconnect(self) -> dict[str, Any]:
        self.connected = False
        logger.info("MicroSD device disconnected")
        return {"status": "disconnected"}

    def identify(self) -> dict[str, Any]:
        return {"name": self.name, "transport": self.transport, "vendor_id": "0x0000", "device_id": "0x0000"}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "card_type": "microSDHC", "speed_class": "Class 10"}

    def diagnostics(self) -> dict[str, Any]:
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "tests": {"card_detected": "passed", "file_system_check": "passed"},
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
