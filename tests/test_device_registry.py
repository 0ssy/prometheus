from devices.registry import DeviceRegistry
from api.device_api import DeviceApi
from api.events import DeviceConnectedEvent, DeviceDisconnectedEvent
from core.event_bus import InMemoryEventBus


class FakeDevice:
    device_id = "dev1"
    transport = "simulated"
    ownership_declared = False

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def read(self) -> None:
        return None

    def write(self, payload: None) -> None:
        pass

    def status(self) -> dict:
        return {"state": "idle"}


class TestDeviceRegistry:
    def test_is_device_api(self):
        registry = DeviceRegistry()
        assert isinstance(registry, DeviceApi)

    def test_register_and_get(self):
        registry = DeviceRegistry()
        device = FakeDevice()
        registry.register(device)
        assert registry.get("dev1") is device

    def test_unregister(self):
        registry = DeviceRegistry()
        device = FakeDevice()
        registry.register(device)
        registry.unregister("dev1")
        assert registry.get("dev1") is None

    def test_unregister_missing_is_safe(self):
        registry = DeviceRegistry()
        registry.unregister("nonexistent")

    def test_list(self):
        registry = DeviceRegistry()
        device = FakeDevice()
        registry.register(device)
        result = registry.list()
        assert len(result) == 1
        assert result[0]["device_id"] == "dev1"
        assert result[0]["transport"] == "simulated"

    def test_register_unregister_publish_events(self):
        bus = InMemoryEventBus()
        connected: list[DeviceConnectedEvent] = []
        disconnected: list[DeviceDisconnectedEvent] = []
        bus.subscribe("device.connected", lambda event: connected.append(event))
        bus.subscribe("device.disconnected", lambda event: disconnected.append(event))
        registry = DeviceRegistry(event_bus=bus)

        registry.register(FakeDevice())
        registry.unregister("dev1")

        assert len(connected) == 1
        assert connected[0].device_id == "dev1"
        assert len(disconnected) == 1
        assert disconnected[0].device_id == "dev1"
