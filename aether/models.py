"""
P3 Aether AI Runtime — persistence models.

Context window state and tool-call history are persisted so agent
workflows are auditable and resumable.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text

from core.database import Base


class AetherContext(Base):
    __tablename__ = "aether_context"

    id = Column(String, primary_key=True)
    session_id = Column(String, index=True, nullable=False)
    window_state = Column(Text, default="{}")  # JSON: short/long memory + retrieval
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AetherToolCall(Base):
    __tablename__ = "aether_tool_calls"

    id = Column(String, primary_key=True)
    session_id = Column(String, index=True, nullable=False)
    tool = Column(String, nullable=False)
    args_json = Column(Text, default="{}")
    result_json = Column(Text, default="{}")
    status = Column(String, default="pending", nullable=False)  # pending|success|error
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
