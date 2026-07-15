from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.orm import Session

from core.database import Base
from core.logger import get_logger

logger = get_logger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Metric(Base):
    """Durable counter snapshot. Upserted on shutdown so counters
    survive restarts (P1 baseline observability requirement)."""

    __tablename__ = "metrics"

    name = Column(String, primary_key=True)
    value = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ObservabilityStore:
    def __init__(self):
        self._metrics: dict[str, int] = defaultdict(int)
        self._traces: list[dict[str, Any]] = []
        self._event_history: list[dict[str, Any]] = []
        self._event_timestamps: list[float] = []
        self._command_timestamps: list[float] = []
        self._window_seconds = 60

    def increment(self, metric_name: str, amount: int = 1) -> None:
        self._metrics[metric_name] += amount

    def record_trace(self, name: str, detail: dict[str, Any]) -> None:
        self._traces.append(
            {"timestamp": _utc_now().isoformat(), "name": name, "detail": detail}
        )

    def record_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_history.append(
            {"timestamp": _utc_now().isoformat(), "event_type": event_type, "payload": payload}
        )
        self.increment(f"events.{event_type}")
        self._event_timestamps.append(time.time())
        self._prune_window(self._event_timestamps)

    def record_command(self, command_name: str) -> None:
        self._command_timestamps.append(time.time())
        self._prune_window(self._command_timestamps)
        self.increment(f"commands.{command_name}")

    def _prune_window(self, timestamps: list[float]) -> None:
        cutoff = time.time() - self._window_seconds
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)

    def _rate_per_sec(self, timestamps: list[float]) -> float:
        if len(timestamps) < 2:
            return 0.0
        span = timestamps[-1] - timestamps[0]
        if span <= 0:
            return 0.0
        return len(timestamps) / span

    def snapshot(
        self,
        status: dict[str, Any] | None = None,
        db_session: Session | None = None,
    ) -> dict[str, Any]:
        subsystems = {}
        if status:
            for key in (
                "kernel",
                "knowledge",
                "simulation",
                "reasoning",
                "hardware",
                "agents",
                "plugins",
                "devices",
                "workflows",
                "background_tasks",
                "storage",
            ):
                subsystems[key] = status.get(key, "Idle")
        result: dict[str, Any] = {
            "metrics": dict(self._metrics),
            "traces": list(self._traces),
            "event_history": list(self._event_history),
            "events_per_sec": round(self._rate_per_sec(list(self._event_timestamps)), 2),
            "commands_per_sec": round(self._rate_per_sec(list(self._command_timestamps)), 2),
            "subsystems": subsystems,
        }
        if db_session is not None:
            result["persisted_metrics"] = self.load_persisted(db_session)
        return result

    def persist_metrics(self, session: Session) -> None:
        """Upsert the current in-memory counters into the ``metrics`` table."""
        now = _utc_now()
        for name, value in self._metrics.items():
            row = session.get(Metric, name)
            if row is None:
                session.add(Metric(name=name, value=value, updated_at=now))
            else:
                row.value = value
                row.updated_at = now
        session.commit()

    def load_persisted(self, session: Session) -> dict[str, int]:
        """Read the last persisted counter snapshot from the DB."""
        return {m.name: m.value for m in session.query(Metric).all()}

    def snapshot_to_db(self, session_factory=None) -> None:
        """Best-effort persistence of counters on shutdown. Degrades
        silently if the database is unavailable (e.g. unit tests)."""
        if session_factory is None:
            from core.database import SessionLocal

            session_factory = SessionLocal
        try:
            with session_factory() as session:
                self.persist_metrics(session)
        except Exception:
            logger.exception("Failed to persist observability metrics")
