"""
Prometheus Knowledge Graph — Interface
-----------------------------------------
assert_fact() and query_facts() are the only two operations Phase
Alpha needs. Everything else (inference, contradiction detection,
confidence decay) is Capability Backlog material — don't build it
until something in the system actually needs it.
"""

from sqlalchemy.orm import Session
from .models import KnowledgeFact
from contracts.reasoning import ReasoningApi
from contracts.event_bus import EventBus
from api.events import FactAssertedEvent
from core.logger import get_logger
from core.event_bus import event_bus as default_event_bus

logger = get_logger(__name__)


class ReasoningStore(ReasoningApi):
    def __init__(self, event_bus: EventBus | None = None):
        self._event_bus = event_bus or default_event_bus

    def assert_fact(
        self, db: Session, subject: str, predicate: str, obj: str, confidence: int = 100
    ) -> KnowledgeFact:
        fact = KnowledgeFact(
            subject=subject, predicate=predicate, object=obj, confidence=confidence
        )
        db.add(fact)
        db.commit()
        db.refresh(fact)
        self._event_bus.publish(
            FactAssertedEvent(
                subject=subject, predicate=predicate, obj=obj, confidence=confidence
            )
        )
        logger.info(f"Asserted fact: {subject} -{predicate}-> {obj}")
        return fact

    def query_facts(
        self, db: Session, subject: str | None = None, predicate: str | None = None
    ) -> list[KnowledgeFact]:
        query = db.query(KnowledgeFact)
        if subject:
            query = query.filter(KnowledgeFact.subject == subject)
        if predicate:
            query = query.filter(KnowledgeFact.predicate == predicate)
        return query.all()


reasoning_store = ReasoningStore()


def assert_fact(
    db: Session, subject: str, predicate: str, obj: str, confidence: int = 100
) -> KnowledgeFact:
    return reasoning_store.assert_fact(db, subject, predicate, obj, confidence)


def query_facts(
    db: Session, subject: str | None = None, predicate: str | None = None
) -> list[KnowledgeFact]:
    return reasoning_store.query_facts(db, subject, predicate)
