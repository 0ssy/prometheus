"""
Prometheus Knowledge Graph — Interface
-----------------------------------------
assert_fact() and query_facts() are the only two operations Phase
Alpha needs. Everything else (inference, contradiction detection,
confidence decay) is Capability Backlog material — don't build it
until something in the system actually needs it.
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from .models import KnowledgeFact
from core.logger import get_logger

logger = get_logger(__name__)


def assert_fact(db: Session, subject: str, predicate: str, obj: str, confidence: int = 100) -> KnowledgeFact:
    fact = KnowledgeFact(subject=subject, predicate=predicate, object=obj, confidence=confidence)
    db.add(fact)
    db.commit()
    db.refresh(fact)
    logger.info(f"Asserted fact: {subject} -{predicate}-> {obj}")
    return fact


def query_facts(db: Session, subject: str | None = None, predicate: str | None = None) -> list[KnowledgeFact]:
    query = db.query(KnowledgeFact)
    if subject:
        query = query.filter(KnowledgeFact.subject == subject)
    if predicate:
        query = query.filter(KnowledgeFact.predicate == predicate)
    return query.all()
