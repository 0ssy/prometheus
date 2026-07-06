from reasoning.graph import ReasoningStore, reasoning_store, assert_fact, query_facts
from api.reasoning_api import ReasoningApi
from reasoning.models import KnowledgeFact
from api.events import FactAssertedEvent
from core.event_bus import InMemoryEventBus


class TestReasoningStore:
    def test_is_reasoning_api(self):
        store = ReasoningStore()
        assert isinstance(store, ReasoningApi)

    def test_assert_and_query(self, db_session):
        store = ReasoningStore()
        fact = store.assert_fact(
            db_session, "device_1", "has_firmware", "v1.0", confidence=100
        )
        assert isinstance(fact, KnowledgeFact)
        assert fact.subject == "device_1"
        assert fact.predicate == "has_firmware"
        assert fact.object == "v1.0"
        assert fact.confidence == 100

        db_session.commit()
        facts = store.query_facts(db_session, subject="device_1")
        assert len(facts) == 1
        assert facts[0].predicate == "has_firmware"

    def test_query_by_predicate(self, db_session):
        store = ReasoningStore()
        store.assert_fact(db_session, "dev1", "status", "online")
        store.assert_fact(db_session, "dev2", "status", "offline")
        db_session.commit()

        facts = store.query_facts(db_session, predicate="status")
        assert len(facts) == 2

    def test_query_no_filters(self, db_session):
        store = ReasoningStore()
        store.assert_fact(db_session, "dev1", "rel", "obj1")
        store.assert_fact(db_session, "dev2", "rel", "obj2")
        db_session.commit()

        facts = store.query_facts(db_session)
        assert len(facts) == 2

    def test_module_level_functions_backward_compat(self, db_session):
        fact = assert_fact(db_session, "device_2", "status", "online")
        assert isinstance(fact, KnowledgeFact)

        facts = query_facts(db_session, subject="device_2")
        assert len(facts) == 1
        assert facts[0].object == "online"

    def test_reasoning_store_singleton(self):
        assert reasoning_store is not None
        assert isinstance(reasoning_store, ReasoningApi)

    def test_assert_fact_publishes_event(self, db_session):
        bus = InMemoryEventBus()
        events: list[FactAssertedEvent] = []
        bus.subscribe("fact.asserted", lambda event: events.append(event))
        store = ReasoningStore(event_bus=bus)

        store.assert_fact(db_session, "devx", "status", "online")

        assert len(events) == 1
        assert events[0].subject == "devx"
