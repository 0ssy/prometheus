"""
Prometheus Knowledge Graph — Data Model
-----------------------------------------
Simplest useful knowledge representation: subject-predicate-object
triples. e.g. ("device_001", "has_firmware", "v2.3.1").
This is not a graph database yet — it's rows that behave like one.
That's enough to prove the concept in Phase Alpha; a real graph
engine (or Neo4j) can replace this later without touching callers,
since everything goes through reasoning/graph.py.
"""

from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from core.database import Base


class KnowledgeFact(Base):
    __tablename__ = "knowledge_facts"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String, index=True, nullable=False)
    predicate = Column(String, index=True, nullable=False)
    object = Column(String, nullable=False)
    confidence = Column(Integer, default=100)  # 0-100, room for uncertainty later
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
