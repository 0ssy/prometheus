from __future__ import annotations

from typing import Any

from hardware.drivers.base import HardwareDriver
from core.logger import get_logger

logger = get_logger(__name__)


class MQTTDriver(HardwareDriver):
    """Simulated MQTT transport driver."""

    name = "mqtt"
    transport = "mqtt"
    connected = False
    capabilities_list = ["connect", "disconnect", "publish", "subscribe", "diagnose"]

    def connect(self) -> dict[str, Any]:
        self.connected = True
        logger.info("MQTT client connected")
        return {"status": "connected", "transport": self.transport}

    def disconnect(self) -> dict[str, Any]:
        self.connected = False
        logger.info("MQTT client disconnected")
        return {"status": "disconnected"}

    def identify(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "transport": self.transport,
            "broker": "mock-broker.local",
            "port": 1883,
        }

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "messages_per_sec": 0, "connected_clients": 1}

    def diagnostics(self) -> dict[str, Any]:
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "tests": {"connection": "passed", "publish": "passed", "subscribe": "passed"},
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


class ModbusDriver(HardwareDriver):
    """Simulated Modbus transport driver."""

    name = "modbus"
    transport = "modbus"
    connected = False
    capabilities_list = [
        "connect",
        "disconnect",
        "read_coils",
        "read_registers",
        "write_register",
        "diagnose",
    ]

    def connect(self) -> dict[str, Any]:
        self.connected = True
        logger.info("Modbus client connected")
        return {"status": "connected", "transport": self.transport}

    def disconnect(self) -> dict[str, Any]:
        self.connected = False
        logger.info("Modbus client disconnected")
        return {"status": "disconnected"}

    def identify(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "transport": self.transport,
            "host": "192.168.1.50",
            "port": 502,
            "unit_id": 1,
        }

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "response_time_ms": 8.0, "active_slaves": 1}

    def diagnostics(self) -> dict[str, Any]:
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "tests": {
                "connection": "passed",
                "read_coils": "passed",
                "read_registers": "passed",
                "write_register": "passed",
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


class OPCUADriver(HardwareDriver):
    """Simulated OPC-UA transport driver."""

    name = "opcua"
    transport = "opcua"
    connected = False
    capabilities_list = [
        "connect",
        "disconnect",
        "browse",
        "read_node",
        "write_node",
        "subscribe",
        "diagnose",
    ]

    def connect(self) -> dict[str, Any]:
        self.connected = True
        logger.info("OPC-UA client connected")
        return {"status": "connected", "transport": self.transport}

    def disconnect(self) -> dict[str, Any]:
        self.connected = False
        logger.info("OPC-UA client disconnected")
        return {"status": "disconnected"}

    def identify(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "transport": self.transport,
            "endpoint": "opc.tcp://mock-server.local:4840",
            "port": 4840,
        }

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "session_active": True, "subscriptions": 0}

    def diagnostics(self) -> dict[str, Any]:
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "tests": {
                "connection": "passed",
                "browse": "passed",
                "read_node": "passed",
                "write_node": "passed",
                "subscribe": "passed",
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


class BACnetDriver(HardwareDriver):
    """Simulated BACnet transport driver."""

    name = "bacnet"
    transport = "bacnet"
    connected = False
    capabilities_list = [
        "connect",
        "disconnect",
        "who_is",
        "read_property",
        "write_property",
        "diagnose",
    ]

    def connect(self) -> dict[str, Any]:
        self.connected = True
        logger.info("BACnet client connected")
        return {"status": "connected", "transport": self.transport}

    def disconnect(self) -> dict[str, Any]:
        self.connected = False
        logger.info("BACnet client disconnected")
        return {"status": "disconnected"}

    def identify(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "transport": self.transport,
            "device_id": 1234,
            "address": "192.168.1.75",
            "port": 47808,
        }

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "devices_discovered": 1, "response_time_ms": 15.0}

    def diagnostics(self) -> dict[str, Any]:
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "tests": {
                "connection": "passed",
                "who_is": "passed",
                "read_property": "passed",
                "write_property": "passed",
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
