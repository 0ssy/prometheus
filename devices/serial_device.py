"""
Prometheus Serial Device (RFC 0001)
-----------------------------------------
First real transport, per RFC 0001's build order — ESP32/STM32 dev
boards show up as a serial port over USB during development, so this
is the highest-value real driver to have working first.

Requires pyserial (added to requirements.txt). Import is wrapped so
that a machine without pyserial installed can still run everything
else (SimulatedDevice, the API, Phase Alpha) without crashing on
import — the error only surfaces if you actually try to use a real
serial device.
"""
from typing import Any
from .base import Device
from core.logger import get_logger

logger = get_logger(__name__)

try:
    import serial as pyserial
    _PYSERIAL_AVAILABLE = True
except ImportError:
    pyserial = None
    _PYSERIAL_AVAILABLE = False


class SerialDevice(Device):
    def __init__(
        self,
        device_id: str,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0,
        ownership_declared: bool = False,
    ):
        if not _PYSERIAL_AVAILABLE:
            raise RuntimeError(
                "pyserial is not installed. Run: pip install pyserial "
                "(it's in requirements.txt — re-run pip install -r requirements.txt)"
            )
        self.device_id = device_id
        self.transport = "serial"
        self.ownership_declared = ownership_declared
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self._conn: Any | None = None

    def connect(self) -> None:
        if self._conn and self._conn.is_open:
            return
        if pyserial is None:
            raise RuntimeError("pyserial is not installed")
        self._conn = pyserial.Serial(self.port, self.baudrate, timeout=self.timeout)
        logger.info(f"Serial device {self.device_id} connected on {self.port} @ {self.baudrate}")

    def disconnect(self) -> None:
        if self._conn and self._conn.is_open:
            self._conn.close()
            logger.info(f"Serial device {self.device_id} disconnected")

    def read(self) -> Any:
        if not self._conn or not self._conn.is_open:
            raise ConnectionError(f"Device {self.device_id} is not connected")
        line = self._conn.readline()
        return line.decode(errors="replace").strip()

    def write(self, payload: Any) -> None:
        if not self._conn or not self._conn.is_open:
            raise ConnectionError(f"Device {self.device_id} is not connected")
        data = payload if isinstance(payload, bytes) else str(payload).encode()
        self._conn.write(data)

    def status(self) -> dict:
        return {
            "connected": bool(self._conn and self._conn.is_open),
            "port": self.port,
            "baudrate": self.baudrate,
        }