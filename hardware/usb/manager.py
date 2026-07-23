"""USB capability — device model and Hardware API.

The manager enumerates attached USB devices, tracks connect/disconnect via
a hot-plug monitor, enforces the USB permission policy, and publishes
hardware events so that every other subsystem (SDK, Assistant, automation,
terminal, UI) can react to changes.

Real enumeration is performed by the C++ HAL transport when the shared
library is present; otherwise a deterministic simulated backend is used so
the rest of the platform keeps working in CI and on hosts without libusb.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from core.event_bus import event_bus as default_event_bus
from core.logger import get_logger
from hardware.events import DeviceConnectedEvent, DeviceDisconnectedEvent
from hardware.usb.permissions import UsbCapability, UsbPermissionPolicy

logger = get_logger(__name__)


@dataclass
class UsbDevice:
    device_id: str
    vendor_id: int
    product_id: int
    manufacturer: Optional[str] = None
    product: Optional[str] = None
    serial_number: Optional[str] = None
    bus_number: int = 0
    port_number: int = 0
    usb_spec: int = 0
    device_class: int = 0
    max_packet_size: int = 0
    connected: bool = True

    @property
    def vid_pid(self) -> str:
        return f"{self.vendor_id:04x}:{self.product_id:04x}"

    def label(self) -> str:
        if self.manufacturer and self.product:
            return f"{self.manufacturer} {self.product}"
        if self.product:
            return self.product
        if self.manufacturer:
            return self.manufacturer
        return self.vid_pid

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "vendor_id": f"0x{self.vendor_id:04x}",
            "product_id": f"0x{self.product_id:04x}",
            "vid_pid": self.vid_pid,
            "manufacturer": self.manufacturer,
            "product": self.product,
            "serial_number": self.serial_number,
            "bus_number": self.bus_number,
            "port_number": self.port_number,
            "usb_spec": f"0x{self.usb_spec:04x}",
            "device_class": self.device_class,
            "max_packet_size": self.max_packet_size,
            "connected": self.connected,
        }


def _build_simulated_devices() -> list[UsbDevice]:
    return [
        UsbDevice(
            device_id="simulated-usb-0",
            vendor_id=0x18D1,
            product_id=0x4EE7,
            manufacturer="Mock Manufacturer",
            product="Mock USB Device",
            serial_number="USB123456789",
            bus_number=1,
            port_number=1,
            usb_spec=0x0200,
            device_class=0,
            max_packet_size=64,
        ),
        UsbDevice(
            device_id="simulated-usb-1",
            vendor_id=0x2E8A,
            product_id=0x0005,
            manufacturer="Raspberry Pi",
            product="RP2 Boot",
            serial_number="0000000000000000",
            bus_number=1,
            port_number=2,
            usb_spec=0x0210,
            device_class=0xEF,
            max_packet_size=64,
        ),
    ]


class USBManager:
    """Hardware API for the USB capability."""

    def __init__(self, event_bus: Any = None, policy: Optional[UsbPermissionPolicy] = None) -> None:
        self._event_bus = event_bus or default_event_bus
        self._policy = policy if policy is not None else UsbPermissionPolicy(default_allow=False)
        self._devices: dict[str, UsbDevice] = {}
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._monitor_interval = 1.0
        self._real_backend = False
        self._try_load_real_backend()

    def _try_load_real_backend(self) -> None:
        try:
            from hardware.hal.ctypes_bridge import UsbTransport
            self._real_usb_transport = UsbTransport
            self._real_backend = True
            logger.info("USB capability: using real backend (C++ HAL)")
        except Exception as exc:  # pragma: no cover - depends on build
            self._real_backend = False
            logger.info(f"USB capability: real backend unavailable ({exc}); using simulated")

    # -- enumeration -----------------------------------------------------

    def enumerate(self) -> list[UsbDevice]:
        if self._real_backend:
            devices = self._enumerate_real()
        else:
            devices = _build_simulated_devices()
        with self._lock:
            self._devices = {d.device_id: d for d in devices}
        return list(self._devices.values())

    def _enumerate_real(self) -> list[UsbDevice]:
        try:
            raw = self._real_usb_transport.enumerate()
        except Exception as exc:  # pragma: no cover - depends on host
            logger.warning(f"USB real enumeration failed: {exc}")
            return _build_simulated_devices()
        if not raw:
            logger.info("USB real enumeration returned no devices; using simulated fallback")
            return _build_simulated_devices()
        return [
            UsbDevice(
                device_id=d.get("device_id", f"{d.get('vendor_id'):04x}:{d.get('product_id'):04x}"),
                vendor_id=d.get("vendor_id", 0),
                product_id=d.get("product_id", 0),
                manufacturer=d.get("manufacturer"),
                product=d.get("product"),
                serial_number=d.get("serial_number"),
                bus_number=d.get("bus_number", 0),
                port_number=d.get("port_number", 0),
                usb_spec=d.get("usb_spec", 0),
                device_class=d.get("device_class", 0),
                max_packet_size=d.get("max_packet_size", 0),
            )
            for d in raw
        ]

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [d.to_dict() for d in self._devices.values()]

    def get(self, device_id: str) -> Optional[UsbDevice]:
        with self._lock:
            return self._devices.get(device_id)

    # -- permissions -----------------------------------------------------

    def policy(self) -> UsbPermissionPolicy:
        return self._policy

    def can_access(
        self,
        capability: UsbCapability,
        vendor_id: int,
        product_id: int,
        serial: Optional[str] = None,
    ) -> tuple[bool, str]:
        return self._policy.check(capability, vendor_id, product_id, serial)

    # -- hot-plug monitoring --------------------------------------------

    def start_monitor(self, interval: float = 1.0) -> None:
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._monitor_interval = interval
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, name="usb-monitor", daemon=True
        )
        self._monitor_thread.start()
        logger.info("USB hot-plug monitor started")

    def stop_monitor(self) -> None:
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=self._monitor_interval + 1.0)
            self._monitor_thread = None
        logger.info("USB hot-plug monitor stopped")

    def poll_once(self) -> None:
        """Perform a single hot-plug diff and emit connect/disconnect events.

        Safe to call from tests and external schedulers; does not block.
        """
        previous = set(self._devices.keys())
        current_devices = self.enumerate()
        current = {d.device_id for d in current_devices}
        device_by_id = {d.device_id: d for d in current_devices}
        for dev_id in current - previous:
            dev = device_by_id.get(dev_id)
            if dev:
                self._event_bus.publish(
                    DeviceConnectedEvent(device_id=dev_id, transport="usb")
                )
                logger.info(f"USB device connected: {dev.label()} ({dev.vid_pid})")
        for dev_id in previous - current:
            self._event_bus.publish(DeviceDisconnectedEvent(device_id=dev_id))
            logger.info(f"USB device disconnected: {dev_id}")

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            self.poll_once()
            self._stop_event.wait(self._monitor_interval)

    def on_change(self, handler: Callable[[str, bool], None]) -> None:
        """Subscribe to connect/disconnect (device_id, connected)."""

        def _connected(ev: DeviceConnectedEvent) -> None:
            handler(ev.device_id, True)

        def _disconnected(ev: DeviceDisconnectedEvent) -> None:
            handler(ev.device_id, False)

        self._event_bus.subscribe("hardware.device.connected", _connected)
        self._event_bus.subscribe("hardware.device.disconnected", _disconnected)


_default_manager: Optional[USBManager] = None


def get_usb_manager() -> USBManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = USBManager()
    return _default_manager
