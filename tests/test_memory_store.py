from memory.store import MemoryStore, memory_store, remember, recall
from api.memory_api import MemoryApi
from memory.models import MemoryEntry
from api.events import MemoryStoredEvent
from core.event_bus import InMemoryEventBus


class TestMemoryStore:
    def test_is_memory_api(self):
        store = MemoryStore()
        assert isinstance(store, MemoryApi)

    def test_remember_and_recall(self, db_session):
        store = MemoryStore()
        entry = store.remember(db_session, "hello world", tag="test")
        assert isinstance(entry, MemoryEntry)
        assert entry.content == "hello world"
        assert entry.tag == "test"
        assert entry.source == "system"

        db_session.commit()
        entries = store.recall(db_session, tag="test")
        assert len(entries) == 1
        assert entries[0].content == "hello world"

    def test_recall_no_tag(self, db_session):
        store = MemoryStore()
        store.remember(db_session, "general memory", tag="general")
        store.remember(db_session, "other memory", tag="other")
        db_session.commit()

        entries = store.recall(db_session)
        assert len(entries) == 2

    def test_recall_with_limit(self, db_session):
        store = MemoryStore()
        for i in range(10):
            store.remember(db_session, f"memory {i}", tag="limited")
        db_session.commit()

        entries = store.recall(db_session, tag="limited", limit=5)
        assert len(entries) == 5

    def test_recall_filters_by_tag(self, db_session):
        store = MemoryStore()
        store.remember(db_session, "tagged", tag="alpha")
        store.remember(db_session, "tagged too", tag="beta")
        db_session.commit()

        entries = store.recall(db_session, tag="alpha")
        assert len(entries) == 1
        assert entries[0].tag == "alpha"

    def test_module_level_functions_backward_compat(self, db_session):
        entry = remember(db_session, "backward compat test", tag="compat")
        assert isinstance(entry, MemoryEntry)

        entries = recall(db_session, tag="compat")
        assert len(entries) == 1
        assert entries[0].content == "backward compat test"

    def test_memory_store_singleton(self):
        assert memory_store is not None
        assert isinstance(memory_store, MemoryApi)

    def test_remember_publishes_event(self, db_session):
        bus = InMemoryEventBus()
        events: list[MemoryStoredEvent] = []
        bus.subscribe("memory.stored", lambda event: events.append(event))
        store = MemoryStore(event_bus=bus)

        store.remember(db_session, "event memory", tag="events", source="test")

        assert len(events) == 1
        assert events[0].tag == "events"
