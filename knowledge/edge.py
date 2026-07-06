from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text

from core.database import Base


class KnowledgeEdge(Base):
    __tablename__ = "knowledge_edges"

    id = Column(Integer, primary_key=True, index=True)
    subject_node_id = Column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False)
    predicate = Column(String, index=True, nullable=False)
    object_node_id = Column(Integer, ForeignKey("knowledge_nodes.id"), nullable=True)
    object_value = Column(String, nullable=True)
    confidence = Column(Float, default=1.0)
    source = Column(String, index=True, nullable=False)
    rationale = Column(Text, default="")
    evidence_json = Column(Text, default="{}")
    supersedes_edge_id = Column(Integer, ForeignKey("knowledge_edges.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
