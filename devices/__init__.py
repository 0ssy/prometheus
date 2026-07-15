from __future__ import annotations

import warnings

warnings.warn(
    "The 'devices' package is deprecated. Import from 'hardware' instead. "
    "This shim will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

from devices.base import Device
from devices.registry import DeviceRegistry, device_registry
from devices.simulated import SimulatedDevice
from devices.serial_device import SerialDevice
from devices.ownership import OwnershipNotDeclaredError, require_ownership_declared

__all__ = [
    "Device",
    "DeviceRegistry",
    "device_registry",
    "SimulatedDevice",
    "SerialDevice",
    "OwnershipNotDeclaredError",
    "require_ownership_declared",
]
