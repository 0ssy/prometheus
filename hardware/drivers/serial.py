from __future__ import annotations

from typing import Any

from hardware.drivers.base import HardwareDriver
from hardware.serial import SerialCapability, get_serial_manager
from core.logger import get_logger

logger = get_logger(__name__)

try:
    import serial as pyserial

    _PYSERIAL_AVAILABLE = True
except ImportError:
    pyserial = None
    _PYSERIAL_AVAILABLE = False


class SerialDriver(HardwareDriver):
    """Serial driver backed by the Serial capability (``hardware.serial``).

    When bound to a real enumerated port it reads live metadata from
    ``SerialManager`` and enforces the permission policy on ``connect()``.
    Actual byte I/O uses pyserial when available; the simulated capability
    backend returns empty frames so the driver contract stays usable in CI.
    """

    name = "serial"
    transport = "serial"
    connected = False
    capabilities_list = ["connect", "disconnect", "read", "write", "diagnose", "configure", "log"]

    def __init__(
        self,
        device_id: str | None = None,
        port: str | None = None,
        baudrate: int = 115200,
        timeout: float = 1.0,
    ) -> None:
        super().__init__()
        self.device_id = device_id
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._conn: Any | None = None

    # -- binding ---------------------------------------------------------

    def _resolve_port(self) -> Any | None:
        manager = get_serial_manager()
        manager.enumerate()
        if self.port:
            return manager.get(self.port)
        ports = manager.enumerate()
        return ports[0] if ports else None

    # -- HardwareDriver contract ----------------------------------------

    def connect(self) -> dict[str, Any]:
        sp = self._resolve_port()
        if sp is None:
            self.connected = False
            return {"status": "no_port", "transport": self.transport}

        ok, why = get_serial_manager().can_access(
            SerialCapability.CONNECT,
            sp.port,
            sp.vendor_id,
            sp.product_id,
            sp.serial_number,
        )
        if not ok:
            self.connected = False
            logger.warning(f"Serial connect denied for {sp.port}: {why}")
            return {"status": "denied", "reason": why, "transport": self.transport}

        self.port = sp.port
        self.baudrate = sp.baud_rate or self.baudrate
        self.device_id = sp.port

        # Attempt a real pyserial connection when available and permitted.
        if _PYSERIAL_AVAILABLE:
            try:
                self._conn = pyserial.Serial(self.port, self.baudrate, timeout=self.timeout)
            except Exception as exc:  # pragma: no cover - depends on host
                logger.debug(f"pyserial open failed for {self.port}: {exc}")

        self.connected = True
        logger.info(f"Serial device {sp.port} connected @ {self.baudrate}")
        return {
            "status": "connected",
            "transport": self.transport,
            "port": self.port,
            "baudrate": self.baudrate,
        }

    def disconnect(self) -> dict[str, Any]:
        if self._conn is not None and getattr(self._conn, "is_open", False):
            try:
                self._conn.close()
            except Exception:  # pragma: no cover
                pass
        self.connected = False
        logger.info("Serial device %s disconnected", self.port)
        return {"status": "disconnected", "transport": self.transport}

    def identify(self) -> dict[str, Any]:
        sp = self._resolve_port()
        if sp is None:
            return {
                "name": self.name,
                "transport": self.transport,
                "port": self.port,
                "baudrate": self.baudrate,
            }
        return {
            "name": self.name,
            "transport": self.transport,
            "port": sp.port,
            "vid_pid": sp.vid_pid,
            "manufacturer": sp.manufacturer,
            "product": sp.product,
            "serial_number": sp.serial_number,
            "baudrate": sp.baud_rate,
        }

    def health(self) -> dict[str, Any]:
        sp = self._resolve_port()
        port = sp.port if sp else self.port
        return {
            "status": "ok" if self.connected else "disconnected",
            "port": port,
        }

    def diagnostics(self) -> dict[str, Any]:
        sp = self._resolve_port()
        port = sp.port if sp else self.port
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "port": port,
            "baudrate": sp.baud_rate if sp else self.baudrate,
            "status": "ok" if self.connected else "disconnected",
        }

    def read(self, length: int = 1024) -> bytes:
        if self._conn is not None and getattr(self._conn, "is_open", False):
            try:
                return self._conn.read(length)
            except Exception:  # pragma: no cover
                return b""
        return get_serial_manager().read(self.port or "", length=length)

    def write(self, data: bytes) -> int:
        if self._conn is not None and getattr(self._conn, "is_open", False):
            try:
                self._conn.write(data)
                return len(data)
            except Exception:  # pragma: no cover
                return 0
        return get_serial_manager().write(self.port or "", data)

    def configure(self, baudrate: int) -> dict[str, Any]:
        if self.port:
            get_serial_manager().configure(self.port, baudrate)
        self.baudrate = baudrate
        return {"status": "configured", "port": self.port, "baudrate": baudrate}

    def read_log(self) -> list[dict[str, Any]]:
        return get_serial_manager().log()

    def simulate(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"driver": self.name, "capability": capability, "simulated": True}

    def verify(self) -> dict[str, Any]:
        sp = self._resolve_port()
        return {"driver": self.name, "verified": sp is not None}

    # -- factory ---------------------------------------------------------

    @classmethod
    def for_port(cls, port: str) -> "SerialDriver":
        return cls(port=port)
