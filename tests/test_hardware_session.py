from __future__ import annotations

import time
from datetime import datetime, timezone


from hardware.session import DeviceSession, DeviceSessionManager


def test_session_manager_create_and_get():
    manager = DeviceSessionManager()
    session = manager.create_session("dev1", "usb", transport="usb")
    assert session.device_id == "dev1"
    assert session.driver_name == "usb"
    assert session.session_id == "usb:dev1"
    fetched = manager.get_session("usb:dev1")
    assert fetched is session


def test_session_manager_list_sessions():
    manager = DeviceSessionManager()
    manager.create_session("dev1", "usb")
    manager.create_session("dev2", "adb")
    sessions = manager.list_sessions()
    assert len(sessions) == 2
    ids = {s.session_id for s in sessions}
    assert ids == {"usb:dev1", "adb:dev2"}


def test_session_manager_close_session():
    manager = DeviceSessionManager()
    manager.create_session("dev1", "usb")
    manager.close_session("usb:dev1")
    assert manager.get_session("usb:dev1") is None


def test_session_manager_refresh_session():
    manager = DeviceSessionManager()
    session = manager.create_session("dev1", "usb")
    old_activity = session.last_activity
    time.sleep(0.01)
    refreshed = manager.refresh_session("usb:dev1")
    assert refreshed is session
    assert session.last_activity > old_activity


def test_session_manager_cleanup_expired():
    manager = DeviceSessionManager()
    session = manager.create_session("dev1", "usb", timeout_seconds=0)
    session.last_activity = datetime(1970, 1, 1, tzinfo=timezone.utc)
    expired = manager.cleanup_expired()
    assert "usb:dev1" in expired
    assert manager.get_session("usb:dev1") is None


def test_device_session_defaults():
    session = DeviceSession(
        session_id="usb:dev1",
        device_id="dev1",
        driver_name="usb",
        transport="usb",
    )
    assert session.retries == 0
    assert session.max_retries == 3
    assert session.timeout_seconds == 300
