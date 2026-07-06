from __future__ import annotations

from core.event_bus import InMemoryEventBus

from hardware.events import (
    DeviceConnectedEvent,
    DeviceDisconnectedEvent,
    BatteryLowEvent,
    FirmwareDetectedEvent,
    DriverFailedEvent,
    SessionExpiredEvent,
)


def test_device_connected_event():
    event = DeviceConnectedEvent(device_id="dev1", transport="usb")
    assert event.event_type == "hardware.device.connected"
    assert event.device_id == "dev1"
    assert event.transport == "usb"


def test_device_disconnected_event():
    event = DeviceDisconnectedEvent(device_id="dev1", reason="user_request")
    assert event.event_type == "hardware.device.disconnected"
    assert event.reason == "user_request"


def test_battery_low_event():
    event = BatteryLowEvent(device_id="dev1", battery_percent=15)
    assert event.event_type == "hardware.battery.low"
    assert event.battery_percent == 15


def test_firmware_detected_event():
    event = FirmwareDetectedEvent(device_id="dev1", firmware_version="1.0", driver_name="fastboot")
    assert event.event_type == "hardware.firmware.detected"
    assert event.firmware_version == "1.0"


def test_driver_failed_event():
    event = DriverFailedEvent(device_id="dev1", driver_name="adb", reason="timeout")
    assert event.event_type == "hardware.driver.failed"
    assert event.driver_name == "adb"
    assert event.reason == "timeout"


def test_session_expired_event():
    event = SessionExpiredEvent(device_id="dev1", session_id="adb:dev1", idle_seconds=600)
    assert event.event_type == "hardware.session.expired"
    assert event.idle_seconds == 600
