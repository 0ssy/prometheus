from core.event_bus import InMemoryEventBus
from devices.registry import DeviceRegistry
from services.epsilon_service import EpsilonService


class FakeDevice:
    device_id = "d1"
    transport = "simulated"
    ownership_declared = True

    def status(self) -> dict:
        return {"connected": True, "battery_health": 0.8, "storage_health": 0.9}


def test_epsilon_service_interfaces_and_diagnostics():
    registry = DeviceRegistry(event_bus=InMemoryEventBus())
    registry.register(FakeDevice())
    epsilon = EpsilonService(device_api=registry)

    defaults = epsilon.register_default_interfaces()
    assert len(defaults["interfaces"]) >= 5
    diagnostics = epsilon.diagnostics("d1")
    assert diagnostics["overall"] == "ok"


def test_epsilon_service_recovery_and_firmware():
    registry = DeviceRegistry(event_bus=InMemoryEventBus())
    registry.register(FakeDevice())
    epsilon = EpsilonService(device_api=registry)

    plan = epsilon.recovery_plan("d1", risk="high")
    assert plan["device_id"] == "d1"
    fw = epsilon.firmware_summary({"format": "bin", "boot_chain": "valid"})
    assert fw["format"] == "bin"


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


def test_epsilon_service_connect_disconnect():
    registry = DeviceRegistry(event_bus=InMemoryEventBus())
    registry.register(FakeDevice())
    epsilon = EpsilonService(device_api=registry)
    epsilon._hal.get_interface = lambda name: StubDriver

    connected = epsilon.connect_device("d1", actor="user", permissions={"device.connect"})
    assert connected["device_id"] == "d1"
    assert "session_id" in connected

    disconnected = epsilon.disconnect_device("d1", actor="user", permissions={"device.disconnect"})
    assert disconnected["disconnected"] is True


def test_epsilon_service_full_diagnostics():
    registry = DeviceRegistry(event_bus=InMemoryEventBus())
    registry.register(FakeDevice())
    epsilon = EpsilonService(device_api=registry)
    session = epsilon._session_manager.create_session("d1", "virtual", transport="virtual")
    report = epsilon.full_diagnostics("d1")
    assert report["device_id"] == "d1"
    assert report["driver"] == "virtual"
    assert report["overall_status"] == "ok"


def test_epsilon_service_firmware_parse():
    epsilon = EpsilonService(device_api=DeviceRegistry(event_bus=InMemoryEventBus()))
    data = b"\x00" * 510 + b"\x55\xAA" + b"EFI PART" + b"\x00" * 500
    result = epsilon.firmware_parse(data)
    assert result["format"] == "uefi"

