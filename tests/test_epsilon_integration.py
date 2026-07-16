from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hardware.compat.adapter import DeviceRegistryAdapter
from core.event_bus import InMemoryEventBus
from epsilon.hal import EpsilonHAL
from services.epsilon_service import EpsilonService


class FakeDevice:
    device_id = "dev1"
    transport = "simulated"
    ownership_declared = True

    def status(self) -> dict:
        return {"connected": True, "battery_health": 0.8, "storage_health": 0.9}


class StubDriver:
    name = "virtual"
    transport = "virtual"
    connected = False

    def __init__(self, **kwargs):
        pass

    def connect(self) -> dict:
        StubDriver.connected = True
        return {"status": "connected"}

    def disconnect(self) -> dict:
        StubDriver.connected = False
        return {"status": "disconnected"}


def test_epsilon_service_hal_integration():
    hal = EpsilonHAL()
    interfaces = hal.list_interfaces()
    assert any(i["name"] == "usb" for i in interfaces)
    driver_cls = hal.get_interface("usb")
    assert driver_cls is not None
    driver = hal.instantiate_driver("usb")
    assert driver.name == "usb"


def test_epsilon_service_diagnostics_with_event_bus():
    bus = InMemoryEventBus()
    events = []
    bus.subscribe("hardware.device.connected", lambda e: events.append(e))
    registry = DeviceRegistryAdapter(event_bus=bus)
    registry.register(FakeDevice())
    eps = EpsilonService(device_api=registry, event_bus=bus)

    session = eps._session_manager.create_session("dev1", "virtual", transport="virtual")
    report = eps._diagnostics.full_report(session)
    assert report["overall_status"] == "ok"
    assert len(events) == 1
    assert events[0].device_id == "dev1"


def test_epsilon_service_recovery_plan_with_digital_twin():
    registry = DeviceRegistryAdapter(event_bus=InMemoryEventBus())
    registry.register(FakeDevice())
    fake_delta = MagicMock()
    fake_delta.build_twin.return_value = {"twin": True}


    def _fake_session_factory(db):
        return None

    eps = EpsilonService(
        device_api=registry,
        delta_service=fake_delta,
        session_factory=_fake_session_factory,
    )
    plan = eps.recovery_plan("dev1", risk="high")
    assert plan["device_id"] == "dev1"
    assert "digital_twin" in plan
    assert plan["digital_twin"] == {"twin": True}


def test_epsilon_service_firmware_parse():
    eps = EpsilonService(device_api=DeviceRegistryAdapter(event_bus=InMemoryEventBus()))
    data = b"\x00" * 510 + b"\x55\xAA" + b"EFI PART" + b"\x00" * 500
    result = eps.firmware_parse(data)
    assert result["format"] == "uefi"


def test_epsilon_service_authorization_denied():
    registry = DeviceRegistryAdapter(event_bus=InMemoryEventBus())
    registry.register(FakeDevice())
    eps = EpsilonService(device_api=registry)
    eps._hal.get_interface = lambda name: StubDriver
    with pytest.raises(RuntimeError, match="Authorization denied"):
        eps.connect_device("dev1", actor="user", permissions=set())
    entries = eps._audit.query(actor="user", action="device.connect", resource="dev1")
    assert len(entries) == 1
    assert entries[0].result == "denied"


def test_epsilon_service_audit_logging():
    registry = DeviceRegistryAdapter(event_bus=InMemoryEventBus())
    registry.register(FakeDevice())
    eps = EpsilonService(device_api=registry, event_bus=InMemoryEventBus())
    eps._hal.get_interface = lambda name: StubDriver
    eps.connect_device("dev1", actor="user", permissions={"device.connect"})
    entries = eps._audit.query(actor="user", action="device.connect", resource="dev1")
    assert len(entries) == 1
    assert entries[0].result == "allowed"
