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
from api.reasoning_api import ReasoningApi
from core.logger import get_logger

logger = get_logger(__name__)


class ReasoningStore(ReasoningApi):
    def assert_fact(
        self, db: Session, subject: str, predicate: str, obj: str, confidence: int = 100
    ) -> KnowledgeFact:
        fact = KnowledgeFact(
            subject=subject, predicate=predicate, object=obj, confidence=confidence
        )
        db.add(fact)
        db.commit()
        db.refresh(fact)
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
