from __future__ import annotations

from hardware.session import DeviceSession, DeviceSessionManager
from hardware.diagnostics import HardwareDiagnostics
from hardware.recovery import HardwareRecovery


def _make_session() -> DeviceSession:
    manager = DeviceSessionManager()
    return manager.create_session("dev1", "usb", transport="usb")


def test_hardware_recovery_assess_risk_low():
    recovery = HardwareRecovery()
    session = _make_session()
    diagnostics = {
        "overall_status": "ok",
        "battery": {"battery_health": 0.9},
        "storage": {"health": "healthy"},
    }
    assert recovery.assess_risk(session, diagnostics) == "low"


def test_hardware_recovery_assess_risk_high():
    recovery = HardwareRecovery()
    session = _make_session()
    diagnostics = {
        "overall_status": "error",
        "battery": {"battery_health": 0.1},
        "storage": {"health": "healthy"},
    }
    assert recovery.assess_risk(session, diagnostics) == "high"


def test_hardware_recovery_plan_recovery():
    recovery = HardwareRecovery()
    session = _make_session()
    diagnostics = {
        "overall_status": "ok",
        "battery": {"battery_health": 0.9},
        "storage": {"health": "healthy"},
    }
    plan = recovery.plan_recovery(session, diagnostics)
    assert plan["device_id"] == "dev1"
    assert plan["risk"] == "low"
    assert "requires_approval" in plan
    assert plan["digital_twin_simulated"] is False


def test_hardware_recovery_recommend():
    recovery = HardwareRecovery()
    options = recovery.recommend("dev1", "high")
    assert len(options) == 4
    actions = [o["action"] for o in options]
    assert "reset" in actions
