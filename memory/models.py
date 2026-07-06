"""
Prometheus Long-Term Memory — Data Model
-----------------------------------------
The simplest possible durable memory: a timestamped, tagged record.
This is intentionally not clever yet. Phase Alpha's job is to prove
memory persists across restarts, not to build semantic search.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, timezone
from core.database import Base


class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    tag = Column(String, index=True, default="general")
    source = Column(String, default="system")  # which agent/plugin wrote this
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
