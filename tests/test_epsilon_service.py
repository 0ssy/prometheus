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
