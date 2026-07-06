import pytest
from agents.manager import AgentManager
from api.agent_api import AgentApi
from api.events import AgentDispatchedEvent
from core.event_bus import InMemoryEventBus


class FakeAgent:
    name = "fake_agent"

    def perform(self, task: dict, context: dict) -> dict:
        return {"ok": True}


class TestAgentManager:
    def test_is_agent_api(self):
        manager = AgentManager()
        assert isinstance(manager, AgentApi)

    def test_register_and_list(self):
        manager = AgentManager()
        agent = FakeAgent()
        manager.register(agent)
        assert manager.list_agents() == ["fake_agent"]

    def test_dispatch(self):
        manager = AgentManager()
        agent = FakeAgent()
        manager.register(agent)
        result = manager.dispatch("fake_agent", {}, {})
        assert result == {"ok": True}

    def test_dispatch_missing_agent_raises(self):
        manager = AgentManager()
        with pytest.raises(ValueError, match="No such agent"):
            manager.dispatch("missing_agent", {}, {})

    def test_dispatch_publishes_event(self):
        bus = InMemoryEventBus()
        events: list[AgentDispatchedEvent] = []
        bus.subscribe("agent.dispatched", lambda event: events.append(event))
        manager = AgentManager(event_bus=bus)
        agent = FakeAgent()
        manager.register(agent)

        manager.dispatch("fake_agent", {"task": "x"}, {})

        assert len(events) == 1
        assert events[0].agent_name == "fake_agent"
