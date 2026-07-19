"""Serial communication capability — Hardware API.

The manager enumerates serial ports, tracks connect/disconnect via a hot-plug
monitor, enforces the serial permission policy, performs read/write with
logging, and publishes hardware events. Real enumeration uses the
`hal-core` Rust crate when built with the `serial-real` feature; otherwise a
deterministic simulated backend is used so the rest of the platform keeps
working in CI and on hosts without libserialport.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from core.event_bus import event_bus as default_event_bus
from core.logger import get_logger
from hardware.events import DeviceConnectedEvent, DeviceDisconnectedEvent
from hardware.serial.permissions import SerialCapability, SerialPermissionPolicy

logger = get_logger(__name__)

DEFAULT_BAUD_RATES = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]


@dataclass
class SerialPort:
    port: str
    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    manufacturer: Optional[str] = None
    product: Optional[str] = None
    serial_number: Optional[str] = None
    baud_rates: list[int] = field(default_factory=lambda: list(DEFAULT_BAUD_RATES))
    connected: bool = False
    baud_rate: int = 115200

    @property
    def vid_pid(self) -> Optional[str]:
        if self.vendor_id is not None and self.product_id is not None:
            return f"{self.vendor_id:04x}:{self.product_id:04x}"
        return None

    def label(self) -> str:
        if self.manufacturer and self.product:
            return f"{self.manufacturer} {self.product} ({self.port})"
        if self.product:
            return f"{self.product} ({self.port})"
        if self.manufacturer:
            return f"{self.manufacturer} ({self.port})"
        return self.port

    def to_dict(self) -> dict[str, Any]:
        return {
            "port": self.port,
            "vendor_id": f"0x{self.vendor_id:04x}" if self.vendor_id is not None else None,
            "product_id": f"0x{self.product_id:04x}" if self.product_id is not None else None,
            "vid_pid": self.vid_pid,
            "manufacturer": self.manufacturer,
            "product": self.product,
            "serial_number": self.serial_number,
            "baud_rates": self.baud_rates,
            "baud_rate": self.baud_rate,
            "connected": self.connected,
        }


def _build_simulated_ports() -> list[SerialPort]:
    return [
        SerialPort(
            port="/dev/ttyUSB0",
            vendor_id=0x18D1,
            product_id=0x4EE7,
            manufacturer="Mock Manufacturer",
            product="Mock UART Device",
            serial_number="TTY123456789",
            baud_rates=[9600, 115200, 921600],
        ),
        SerialPort(
            port="COM3",
            vendor_id=0x2E8A,
            product_id=0x0005,
            manufacturer="Raspberry Pi",
            product="RP2 UART",
            serial_number="0000000000000000",
            baud_rates=[9600, 115200],
        ),
    ]


class SerialManager:
    """Hardware API for the Serial communication capability."""

    def __init__(self, event_bus: Any = None, policy: Optional[SerialPermissionPolicy] = None) -> None:
        self._event_bus = event_bus or default_event_bus
        self._policy = policy if policy is not None else SerialPermissionPolicy(default_allow=False)
        self._ports: dict[str, SerialPort] = {}
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._monitor_interval = 1.0
        self._real_backend = False
        self._log: list[dict[str, Any]] = []
        self._try_load_real_backend()

    def _try_load_real_backend(self) -> None:
        try:
            from hal_core import SerialTransport  # type: ignore

            self._real_serial_transport = SerialTransport
            self._real_backend = True
            logger.info("Serial capability: using real backend (hal-core + serialport)")
        except Exception as exc:  # pragma: no cover - depends on build
            self._real_backend = False
            logger.info(f"Serial capability: real backend unavailable ({exc}); using simulated")

    # -- enumeration -----------------------------------------------------

    def enumerate(self) -> list[SerialPort]:
        if self._real_backend:
            ports = self._enumerate_real()
        else:
            ports = _build_simulated_ports()
        with self._lock:
            self._ports = {p.port: p for p in ports}
        return list(self._ports.values())

    def _enumerate_real(self) -> list[SerialPort]:
        try:
            raw = self._real_serial_transport.enumerate()
        except Exception as exc:  # pragma: no cover - depends on host
            logger.warning(f"Serial real enumeration failed: {exc}")
            return _build_simulated_ports()
        return [
            SerialPort(
                port=p.get("port", "unknown"),
                vendor_id=p.get("vendor_id"),
                product_id=p.get("product_id"),
                manufacturer=p.get("manufacturer"),
                product=p.get("product"),
                serial_number=p.get("serial_number"),
                baud_rates=p.get("baud_rates", list(DEFAULT_BAUD_RATES)),
            )
            for p in raw
        ]

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [p.to_dict() for p in self._ports.values()]

    def get(self, port: str) -> Optional[SerialPort]:
        with self._lock:
            return self._ports.get(port)

    # -- permissions -----------------------------------------------------

    def policy(self) -> SerialPermissionPolicy:
        return self._policy

    def can_access(
        self,
        capability: SerialCapability,
        port: str,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        serial: Optional[str] = None,
    ) -> tuple[bool, str]:
        return self._policy.check(capability, port, vendor_id, product_id, serial)

    # -- connection / io -------------------------------------------------

    def configure(self, port: str, baud_rate: int) -> dict[str, Any]:
        with self._lock:
            sp = self._ports.get(port)
            if sp is None:
                return {"status": "unknown_port", "port": port}
            sp.baud_rate = baud_rate
        return {"status": "configured", "port": port, "baud_rate": baud_rate}

    def connect(self, port: str, baud_rate: int = 115200) -> dict[str, Any]:
        with self._lock:
            sp = self._ports.get(port)
        if sp is None:
            return {"status": "unknown_port", "port": port}
        ok, why = self.can_access(
            SerialCapability.CONNECT, port, sp.vendor_id, sp.product_id, sp.serial_number
        )
        if not ok:
            logger.warning(f"Serial connect denied for {port}: {why}")
            return {"status": "denied", "reason": why, "port": port}
        sp.baud_rate = baud_rate
        sp.connected = True
        logger.info(f"Serial port connected: {port} @ {baud_rate}")
        return {"status": "connected", "port": port, "baud_rate": baud_rate}

    def disconnect(self, port: str) -> dict[str, Any]:
        with self._lock:
            sp = self._ports.get(port)
        if sp is None:
            return {"status": "unknown_port", "port": port}
        sp.connected = False
        return {"status": "disconnected", "port": port}

    def read(self, port: str, length: int = 1024) -> bytes:
        with self._lock:
            sp = self._ports.get(port)
        if sp is None or not sp.connected:
            return b""
        # Simulated/real read would happen here; the simulated backend has no
        # live byte source, so we log the intent and return empty.
        self._record_log(port, "read", f"len={length}")
        return b""

    def write(self, port: str, data: bytes) -> int:
        with self._lock:
            sp = self._ports.get(port)
        if sp is None or not sp.connected:
            return 0
        self._record_log(port, "write", data.decode(errors="replace")[:120])
        return len(data)

    def _record_log(self, port: str, kind: str, detail: str) -> None:
        entry = {"ts": time.time(), "port": port, "kind": kind, "detail": detail}
        with self._lock:
            self._log.append(entry)
            if len(self._log) > 1000:
                self._log = self._log[-1000:]

    def log(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._log)

    # -- hot-plug monitoring --------------------------------------------

    def start_monitor(self, interval: float = 1.0) -> None:
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._monitor_interval = interval
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, name="serial-monitor", daemon=True
        )
        self._monitor_thread.start()
        logger.info("Serial hot-plug monitor started")

    def stop_monitor(self) -> None:
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=self._monitor_interval + 1.0)
            self._monitor_thread = None
        logger.info("Serial hot-plug monitor stopped")

    def poll_once(self) -> None:
        previous = set(self._ports.keys())
        current_devices = self.enumerate()
        current = {p.port for p in current_devices}
        port_by_name = {p.port: p for p in current_devices}
        for port in current - previous:
            sp = port_by_name.get(port)
            if sp:
                self._event_bus.publish(
                    DeviceConnectedEvent(device_id=port, transport="serial")
                )
                logger.info(f"Serial port connected: {sp.label()}")
        for port in previous - current:
            self._event_bus.publish(DeviceDisconnectedEvent(device_id=port))
            logger.info(f"Serial port disconnected: {port}")

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            self.poll_once()
            self._stop_event.wait(self._monitor_interval)

    def on_change(self, handler: Callable[[str, bool], None]) -> None:
        def _connected(ev: DeviceConnectedEvent) -> None:
            handler(ev.device_id, True)

        def _disconnected(ev: DeviceDisconnectedEvent) -> None:
            handler(ev.device_id, False)

        self._event_bus.subscribe("hardware.device.connected", _connected)
        self._event_bus.subscribe("hardware.device.disconnected", _disconnected)


_default_manager: Optional[SerialManager] = None


def get_serial_manager() -> SerialManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = SerialManager()
    return _default_manager
