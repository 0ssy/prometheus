from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from api.events import Event


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(kw_only=True)
class HardwareEvent(Event):
    """Base event for all hardware-related events."""
    device_id: str = ""


@dataclass
class DeviceConnectedEvent(HardwareEvent):
    transport: str = ""

    def __post_init__(self) -> None:
        self.event_type = "hardware.device.connected"


@dataclass
class DeviceDisconnectedEvent(HardwareEvent):
    reason: str = ""

    def __post_init__(self) -> None:
        self.event_type = "hardware.device.disconnected"


@dataclass
class DeviceUnresponsiveEvent(HardwareEvent):
    timeout_seconds: int = 0

    def __post_init__(self) -> None:
        self.event_type = "hardware.device.unresponsive"


@dataclass
class BatteryLowEvent(HardwareEvent):
    battery_percent: int = 0

    def __post_init__(self) -> None:
        self.event_type = "hardware.battery.low"


@dataclass
class FirmwareDetectedEvent(HardwareEvent):
    firmware_version: str = ""
    driver_name: str = ""

    def __post_init__(self) -> None:
        self.event_type = "hardware.firmware.detected"


@dataclass
class DriverFailedEvent(HardwareEvent):
    driver_name: str = ""
    reason: str = ""

    def __post_init__(self) -> None:
        self.event_type = "hardware.driver.failed"


@dataclass
class SessionExpiredEvent(HardwareEvent):
    session_id: str = ""
    idle_seconds: int = 0

    def __post_init__(self) -> None:
        self.event_type = "hardware.session.expired"
