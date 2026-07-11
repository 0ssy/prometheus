"""
Prometheus Local Database
-------------------------
SQLite for now (per the plan: SQLite -> PostgreSQL later). Everything
else — memory, knowledge graph, device registry — writes through
this one engine/session pattern so swapping to Postgres later is a
one-line change, not a rewrite.
"""

import os
import shutil
import sqlite3
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.exc import DatabaseError as SQLAlchemyDatabaseError
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import config
from core.logger import get_logger
from core.event_bus import event_bus

logger = get_logger(__name__)

os.makedirs(os.path.dirname(config.db_path), exist_ok=True)

engine = create_engine(
    f"sqlite:///{config.db_path}",
    connect_args={"check_same_thread": False},  # needed for FastAPI's threaded requests
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(String, primary_key=True, index=True)
    device_id = Column(String, index=True, nullable=False)
    failure_mode = Column(String, nullable=False)
    status = Column(String, default="running")
    progress = Column(String, default="0%")
    risk = Column(String, nullable=True)
    confidence = Column(String, nullable=True)
    recovered = Column(String, nullable=True)
    impact = Column(String, nullable=True)
    result_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)


def get_db():
    """FastAPI dependency: yields a session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called once at startup.

    If the existing SQLite file is corrupted (bad header / disk fault),
    quarantine it to `<path>.corrupted.<timestamp>` and recreate a fresh
    schema so Prometheus can still boot instead of crashing.
    """
    global engine, SessionLocal
    # Import models here so they register with Base before create_all
    from memory.models import MemoryEntry  # noqa
    from reasoning.models import KnowledgeFact  # noqa
    from knowledge.node import KnowledgeNode  # noqa
    from knowledge.edge import KnowledgeEdge  # noqa
    from knowledge.learning import LearningExperience  # noqa

    try:
        Base.metadata.create_all(bind=engine)
    except (sqlite3.DatabaseError, SQLAlchemyDatabaseError):
        db_path = engine.url.database
        if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
            logger.warning("Corrupted SQLite database detected at %s — quarantining", db_path)
            try:
                engine.dispose()
            except Exception:
                pass
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            corrupt_path = f"{db_path}.corrupted.{stamp}"
            shutil.move(db_path, corrupt_path)
            logger.warning("Moved corrupt database to %s; recreating fresh schema", corrupt_path)
            # Rebuild the engine against the now-fresh path so the rest of
            # boot (SessionLocal, registered db_engine) uses a valid
            # connection rather than the moved/corrupt one.
            fresh_engine = create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False},
            )
            engine = fresh_engine
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            try:
                event_bus.publish(
                    DatabaseCorruptedEvent(path=db_path, quarantined_to=corrupt_path)
                )
            except Exception:
                pass
            Base.metadata.create_all(bind=engine)
