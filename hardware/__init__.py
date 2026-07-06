from __future__ import annotations

from hardware.hal.interface import HardwareInterface
from hardware.hal.manager import HALManager
from hardware.hal.registry import HardwareRegistry
from hardware.hal.capability_mapper import CapabilityMapper
from hardware.drivers.base import HardwareDriver
from hardware.drivers.usb import USBDriver
from hardware.drivers.adb import ADBDriver
from hardware.drivers.fastboot import FastbootDriver
from hardware.drivers.network import NetworkDriver
from hardware.drivers.virtual import VirtualDriver
from hardware.session import DeviceSession, DeviceSessionManager
from hardware.diagnostics import HardwareDiagnostics
from hardware.recovery import HardwareRecovery
from hardware.events import (
    HardwareEvent,
    DeviceConnectedEvent,
    DeviceDisconnectedEvent,
    DeviceUnresponsiveEvent,
    BatteryLowEvent,
    FirmwareDetectedEvent,
    DriverFailedEvent,
    SessionExpiredEvent,
)

__all__ = [
    "HardwareInterface",
    "HALManager",
    "HardwareRegistry",
    "CapabilityMapper",
    "HardwareDriver",
    "USBDriver",
    "ADBDriver",
    "FastbootDriver",
    "NetworkDriver",
    "VirtualDriver",
    "DeviceSession",
    "DeviceSessionManager",
    "HardwareDiagnostics",
    "HardwareRecovery",
    "HardwareEvent",
    "DeviceConnectedEvent",
    "DeviceDisconnectedEvent",
    "DeviceUnresponsiveEvent",
    "BatteryLowEvent",
    "FirmwareDetectedEvent",
    "DriverFailedEvent",
    "SessionExpiredEvent",
]
