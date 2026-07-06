"""
Prometheus Memory Store
------------------------
Thin interface over MemoryEntry. Agents and plugins call these
functions instead of touching the database directly — that's the
seam that lets us swap in a vector store or richer recall logic
later without changing every caller.
"""
from sqlalchemy.orm import Session
from .models import MemoryEntry
from core.logger import get_logger

logger = get_logger(__name__)


def remember(db: Session, content: str, tag: str = "general", source: str = "system") -> MemoryEntry:
    entry = MemoryEntry(content=content, tag=tag, source=source)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    logger.info(f"Stored memory [{tag}] from {source}: {content[:60]}")
    return entry


def recall(db: Session, tag: str | None = None, limit: int = 50) -> list[MemoryEntry]:
    query = db.query(MemoryEntry)
    if tag:
        query = query.filter(MemoryEntry.tag == tag)
    return query.order_by(MemoryEntry.created_at.desc()).limit(limit).all()
