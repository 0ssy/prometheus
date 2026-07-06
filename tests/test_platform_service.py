from core.event_bus import InMemoryEventBus
from memory.store import MemoryStore
from reasoning.graph import ReasoningStore
from devices.registry import DeviceRegistry
from agents.manager import AgentManager
from plugins.manager import PluginManager
from services.platform_service import PlatformService


class FakeDevice:
    def __init__(self):
        self.device_id = "dev-2"
        self.transport = "simulated"
        self.ownership_declared = True
        self._value = None

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def read(self):
        return self._value

    def write(self, payload) -> None:
        self._value = payload

    def status(self) -> dict:
        return {"connected": True, "last_value": self._value}


def test_platform_service_write_device_publishes_event():
    bus = InMemoryEventBus()
    device_api = DeviceRegistry(event_bus=bus)
    service = PlatformService(
        plugin_api=PluginManager(event_bus=bus),
        agent_api=AgentManager(event_bus=bus),
        device_api=device_api,
        memory_api=MemoryStore(event_bus=bus),
        reasoning_api=ReasoningStore(event_bus=bus),
        event_bus=bus,
    )
    received: list[str] = []
    bus.subscribe("device.wrote", lambda event: received.append(event.value))
    device_api.register(FakeDevice())

    result = service.write_device("dev-2", value="abc")

    assert result["device_id"] == "dev-2"
    assert received == ["abc"]
