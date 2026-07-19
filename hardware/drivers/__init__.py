from __future__ import annotations

from hardware.drivers.base import HardwareDriver
from hardware.drivers.nfc_rfid import NFCDriver, RFIDDriver
from hardware.drivers.usb import USBDriver
from hardware.drivers.serial import SerialDriver
from hardware.hal.registry import HardwareRegistry
from core.logger import get_logger

logger = get_logger(__name__)

# Register device-bound drivers with the singleton HAL registry so they are
# auto-discovered by the platform alongside the other simulated drivers.
try:
    HardwareRegistry.instance().register(USBDriver)
    HardwareRegistry.instance().register(SerialDriver)
except Exception as exc:  # pragma: no cover - registry guards duplicates
    logger.debug(f"Driver already registered: {exc}")

__all__ = ["HardwareDriver", "NFCDriver", "RFIDDriver", "USBDriver", "SerialDriver"]
