from __future__ import annotations

from hardware.session import DeviceSession, DeviceSessionManager
from hardware.diagnostics import HardwareDiagnostics


def test_hardware_diagnostics_full_report():
    manager = DeviceSessionManager()
    session = manager.create_session("dev1", "usb", transport="usb")
    diagnostics = HardwareDiagnostics()
    report = diagnostics.full_report(session)
    assert report["session_id"] == session.session_id
    assert report["device_id"] == "dev1"
    assert report["driver"] == "usb"
    assert report["battery"]["battery_health"] == 0.9
    assert report["temperature"]["temperature_celsius"] == 38.5
    assert report["storage"]["health"] == "healthy"
    assert report["overall_status"] == "ok"


def test_hardware_diagnostics_battery_health():
    manager = DeviceSessionManager()
    session = manager.create_session("dev1", "adb", transport="adb")
    diagnostics = HardwareDiagnostics()
    battery = diagnostics.battery_health(session)
    assert battery["session_id"] == session.session_id
    assert battery["charging"] is False
    assert battery["cycle_count"] == 42


def test_hardware_diagnostics_temperature():
    manager = DeviceSessionManager()
    session = manager.create_session("dev1", "fastboot", transport="usb")
    diagnostics = HardwareDiagnostics()
    temp = diagnostics.temperature(session)
    assert temp["status"] == "normal"
    assert temp["threshold_celsius"] == 80.0


def test_hardware_diagnostics_storage():
    manager = DeviceSessionManager()
    session = manager.create_session("dev1", "network", transport="network")
    diagnostics = HardwareDiagnostics()
    storage = diagnostics.storage(session)
    assert storage["total_gb"] == 128.0
    assert storage["available_gb"] == 64.0
    assert storage["health"] == "healthy"
