from __future__ import annotations

from typing import Any

from hardware.drivers.base import HardwareDriver
from core.logger import get_logger

logger = get_logger(__name__)

try:
    import serial as pyserial

    _PYSERIAL_AVAILABLE = True
except ImportError:
    pyserial = None
    _PYSERIAL_AVAILABLE = False


class SerialDriver(HardwareDriver):
    """Real serial transport driver.

    Requires pyserial. Import is wrapped so that a machine without
    pyserial installed can still run everything else without crashing
    on import — the error only surfaces if you actually try to use a
    real serial device.
    """

    name = "serial"
    transport = "serial"
    connected = False
    capabilities_list = ["connect", "disconnect", "read", "write", "diagnose"]

    def __init__(
        self,
        device_id: str,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0,
    ) -> None:
        if not _PYSERIAL_AVAILABLE:
            raise RuntimeError(
                "pyserial is not installed. Run: pip install pyserial"
            )
        self.device_id = device_id
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._conn: Any | None = None

    def connect(self) -> dict[str, Any]:
        if self._conn and self._conn.is_open:
            return {"status": "connected", "transport": self.transport}
        if pyserial is None:
            raise RuntimeError("pyserial is not installed")
        self._conn = pyserial.Serial(self.port, self.baudrate, timeout=self.timeout)
        self.connected = True
        logger.info(
            "Serial device %s connected on %s @ %s", self.device_id, self.port, self.baudrate
        )
        return {"status": "connected", "transport": self.transport, "port": self.port}

    def disconnect(self) -> dict[str, Any]:
        if self._conn and self._conn.is_open:
            self._conn.close()
            logger.info("Serial device %s disconnected", self.device_id)
        self.connected = False
        return {"status": "disconnected"}

    def identify(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "transport": self.transport,
            "port": self.port,
            "baudrate": self.baudrate,
        }

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.connected else "disconnected",
            "port": self.port,
        }

    def diagnostics(self) -> dict[str, Any]:
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "port": self.port,
            "baudrate": self.baudrate,
            "status": "ok" if self.connected else "disconnected",
        }

    def read(self, length: int = 1024) -> bytes:
        if not self._conn or not self._conn.is_open:
            raise ConnectionError(f"Device {self.device_id} is not connected")
        line = self._conn.readline()
        return line

    def write(self, data: bytes) -> int:
        if not self._conn or not self._conn.is_open:
            raise ConnectionError(f"Device {self.device_id} is not connected")
        self._conn.write(data)
        return len(data)

    def simulate(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"driver": self.name, "capability": capability, "simulated": True}

    def verify(self) -> dict[str, Any]:
        return {"driver": self.name, "verified": True}
