from core.event_bus import InMemoryEventBus
from core.capabilities import CapabilityManager
from core.observability import ObservabilityStore
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
        capability_api=CapabilityManager(event_bus=bus),
        device_api=device_api,
        memory_api=MemoryStore(event_bus=bus),
        reasoning_api=ReasoningStore(event_bus=bus),
        event_bus=bus,
        observability=ObservabilityStore(),
    )
    received: list[str] = []
    bus.subscribe("device.wrote", lambda event: received.append(event.value))
    device_api.register(FakeDevice())

    result = service.write_device("dev-2", value="abc")

    assert result["device_id"] == "dev-2"
    assert received == ["abc"]


def test_platform_service_registers_device_capabilities():
    bus = InMemoryEventBus()
    capability_api = CapabilityManager(event_bus=bus)
    service = PlatformService(
        plugin_api=PluginManager(event_bus=bus),
        agent_api=AgentManager(event_bus=bus),
        capability_api=capability_api,
        device_api=DeviceRegistry(event_bus=bus),
        memory_api=MemoryStore(event_bus=bus),
        reasoning_api=ReasoningStore(event_bus=bus),
        event_bus=bus,
        observability=ObservabilityStore(),
    )

    service.register_simulated_device("sim-1")
    caps = service.list_capabilities(prefix="device.sim-1")
    names = {cap["name"] for cap in caps}

    assert "device.sim-1.connect" in names
    assert "device.sim-1.read" in names
    assert "device.sim-1.write" in names
    assert "device.sim-1.recover" in names
    assert "device.sim-1.simulate" in names


def test_platform_service_beta_workflow_records_result(db_session):
    bus = InMemoryEventBus()
    capability_api = CapabilityManager(event_bus=bus)
    memory_api = MemoryStore(event_bus=bus)
    reasoning_api = ReasoningStore(event_bus=bus)
    service = PlatformService(
        plugin_api=PluginManager(event_bus=bus),
        agent_api=AgentManager(event_bus=bus),
        capability_api=capability_api,
        device_api=DeviceRegistry(event_bus=bus),
        memory_api=memory_api,
        reasoning_api=reasoning_api,
        event_bus=bus,
        observability=ObservabilityStore(),
    )

    service.register_simulated_device("sim-beta")
    result = service.run_beta_workflow(
        db=db_session, device_id="sim-beta", failure_mode="disconnect", execute=False
    )

    assert result["recorded"] is True
    assert result["simulation"]["failure_mode"] == "disconnect"
    assert result["reasoning"]["recommendation"]["recommended_capability"] == "device.sim-beta.recover"
