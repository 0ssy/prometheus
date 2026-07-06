"""
Prometheus Local Database
-------------------------
SQLite for now (per the plan: SQLite -> PostgreSQL later). Everything
else — memory, knowledge graph, device registry — writes through
this one engine/session pattern so swapping to Postgres later is a
one-line change, not a rewrite.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import config

os.makedirs(os.path.dirname(config.db_path), exist_ok=True)

engine = create_engine(
    f"sqlite:///{config.db_path}",
    connect_args={"check_same_thread": False},  # needed for FastAPI's threaded requests
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


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
    from memory.models import MemoryEntry           # noqa
    from reasoning.models import KnowledgeFact       # noqa
    Base.metadata.create_all(bind=engine)
