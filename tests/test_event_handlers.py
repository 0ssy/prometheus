from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.events import DeviceConnectedEvent, DeviceWriteEvent, PluginRanEvent
from core.database import Base as PrometheusBase
from core.event_bus import InMemoryEventBus
from memory.store import MemoryStore
from reasoning.graph import ReasoningStore
from services.event_handlers import PlatformEventHandlers


def test_event_handlers_project_events_to_memory_and_reasoning():
    engine = create_engine("sqlite:///:memory:")
    PrometheusBase.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    event_bus = InMemoryEventBus()
    memory_api = MemoryStore(event_bus=event_bus)
    reasoning_api = ReasoningStore(event_bus=event_bus)
    handlers = PlatformEventHandlers(
        event_bus=event_bus,
        session_factory=SessionLocal,
        memory_api=memory_api,
        reasoning_api=reasoning_api,
    )
    handlers.bind()

    event_bus.publish(DeviceConnectedEvent(device_id="dev-1", transport="simulated"))
    event_bus.publish(DeviceWriteEvent(device_id="dev-1", value="42"))
    event_bus.publish(PluginRanEvent(plugin_name="echo", result={"ok": True}))

    with SessionLocal() as session:
        facts = reasoning_api.query_facts(session, subject="dev-1")
        memory = memory_api.recall(session, tag="plugin_event")

    assert any(f.predicate == "event" and f.object == "connected" for f in facts)
    assert any(f.predicate == "wrote" and f.object == "42" for f in facts)
    assert len(memory) == 1

    engine.dispose()
