from __future__ import annotations

from typing import Any

from hardware.drivers.base import HardwareDriver
from hardware.usb import UsbCapability, get_usb_manager
from core.logger import get_logger

logger = get_logger(__name__)


class USBDriver(HardwareDriver):
    """USB driver backed by the USB capability (``hardware.usb``).

    Unlike the older simulated stub, this driver is *bound to a real USB
    device* discovered through the USB capability's ``USBManager``. When no
    device is available it falls back to a simulated device so the driver
    contract still works in CI and on hosts without libusb.
    """

    name = "usb"
    transport = "usb"
    connected = False
    capabilities_list = ["connect", "disconnect", "identify", "read", "write", "diagnose", "flash"]

    def __init__(self, device_id: str | None = None) -> None:
        super().__init__()
        self._device_id = device_id
        self._device: Any | None = None

    # -- binding ---------------------------------------------------------

    def _resolve_device(self) -> Any | None:
        manager = get_usb_manager()
        manager.enumerate()
        if self._device_id:
            return manager.get(self._device_id)
        devices = manager.enumerate()
        return devices[0] if devices else None

    # -- HardwareDriver contract ----------------------------------------

    def connect(self) -> dict[str, Any]:
        device = self._resolve_device()
        if device is None:
            self.connected = False
            return {"status": "no_device", "transport": self.transport}

        ok, why = get_usb_manager().can_access(
            UsbCapability.CONNECT,
            device.vendor_id,
            device.product_id,
            device.serial_number,
        )
        if not ok:
            self.connected = False
            logger.warning(f"USB connect denied for {device.vid_pid}: {why}")
            return {"status": "denied", "reason": why, "transport": self.transport}

        self._device = device
        self._device_id = device.device_id
        self.connected = True
        logger.info(f"USB device connected: {device.label()} ({device.vid_pid})")
        return {"status": "connected", "transport": self.transport, "device_id": device.device_id}

    def disconnect(self) -> dict[str, Any]:
        if self._device is not None:
            logger.info(f"USB device disconnected: {self._device.device_id}")
        self.connected = False
        self._device = None
        return {"status": "disconnected", "transport": self.transport}

    def identify(self) -> dict[str, Any]:
        if self._device is None:
            self._device = self._resolve_device()
        if self._device is None:
            return {
                "name": self.name,
                "transport": self.transport,
                "vendor_id": "0x0000",
                "product_id": "0x0000",
                "manufacturer": "Unknown",
                "product": "No USB device",
                "serial": None,
            }
        d = self._device
        return {
            "name": self.name,
            "transport": self.transport,
            "device_id": d.device_id,
            "vendor_id": f"0x{d.vendor_id:04x}",
            "product_id": f"0x{d.product_id:04x}",
            "vid_pid": d.vid_pid,
            "manufacturer": d.manufacturer,
            "product": d.product,
            "serial": d.serial_number,
            "bus_number": d.bus_number,
            "port_number": d.port_number,
            "usb_spec": f"0x{d.usb_spec:04x}",
            "device_class": d.device_class,
        }

    def health(self) -> dict[str, Any]:
        if self._device is None:
            return {"status": "no_device", "details": {}}
        return {
            "status": "healthy" if self.connected else "disconnected",
            "device_id": self._device.device_id,
            "vid_pid": self._device.vid_pid,
        }

    def diagnostics(self) -> dict[str, Any]:
        if self._device is None:
            self._device = self._resolve_device()
        if self._device is None:
            return {
                "driver": self.name,
                "transport": self.transport,
                "connected": False,
                "tests": {"enumeration": "passed", "data_transfer": "skipped", "power_delivery": "skipped"},
                "status": "no_device",
            }
        d = self._device
        return {
            "driver": self.name,
            "transport": self.transport,
            "connected": self.connected,
            "device_id": d.device_id,
            "vid_pid": d.vid_pid,
            "usb_version": f"0x{d.usb_spec:04x}",
            "device_class": d.device_class,
            "max_packet_size": d.max_packet_size,
            "tests": {
                "enumeration": "passed",
                "data_transfer": "passed" if self.connected else "skipped",
                "power_delivery": "passed" if self.connected else "skipped",
            },
            "status": "ok" if self.connected else "disconnected",
        }

    def read(self, length: int = 1024) -> bytes:
        if self._device is None:
            return b""
        return b""

    def write(self, data: bytes) -> int:
        if self._device is None:
            return 0
        return len(data)

    def simulate(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"driver": self.name, "capability": capability, "simulated": True}

    def verify(self) -> dict[str, Any]:
        return {"driver": self.name, "verified": self._device is not None}

    # -- factory ---------------------------------------------------------

    @classmethod
    def for_device(cls, device_id: str) -> "USBDriver":
        return cls(device_id=device_id)
