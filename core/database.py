"""
Prometheus Local Database
-------------------------
SQLite for now (per the plan: SQLite -> PostgreSQL later). Everything
else — memory, knowledge graph, device registry — writes through
this one engine/session pattern so swapping to Postgres later is a
one-line change, not a rewrite.
"""

import os
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timezone
from .config import config

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
    """Create all tables. Called once at startup."""
    # Import models here so they register with Base before create_all
    from memory.models import MemoryEntry  # noqa
    from reasoning.models import KnowledgeFact  # noqa
    from knowledge.node import KnowledgeNode  # noqa
    from knowledge.edge import KnowledgeEdge  # noqa
    from knowledge.learning import LearningExperience  # noqa

    Base.metadata.create_all(bind=engine)
