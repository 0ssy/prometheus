"""
Security: Auditing (Epsilon / Hephaestus phase)
-----------------------------------------------
Logs every security-relevant event. All hardware operations are auditable:
every authorization decision and integrity result should produce an entry.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AuditEntry:
    entry_id: str
    timestamp: datetime
    actor: str
    action: str
    resource: str
    result: str
    metadata: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "action": self.action,
            "resource": self.resource,
            "result": self.result,
            "metadata": self.metadata,
            "session_id": self.session_id,
        }


class AuditLogger:
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._lock = Lock()

    def log(self, entry: AuditEntry) -> None:
        with self._lock:
            self._entries.append(entry)
        logger.info(
            "Audit: actor=%s action=%s resource=%s result=%s",
            entry.actor,
            entry.action,
            entry.resource,
            entry.result,
        )

    def record(
        self,
        actor: str,
        action: str,
        resource: str,
        result: str,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            timestamp=_utc_now(),
            actor=actor,
            action=action,
            resource=resource,
            result=result,
            metadata=dict(metadata or {}),
            session_id=session_id,
        )
        self.log(entry)
        return entry

    def query(
        self,
        actor: str | None = None,
        action: str | None = None,
        resource: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[AuditEntry]:
        with self._lock:
            entries = list(self._entries)
        results: list[AuditEntry] = []
        for entry in entries:
            if actor is not None and entry.actor != actor:
                continue
            if action is not None and entry.action != action:
                continue
            if resource is not None and entry.resource != resource:
                continue
            if start_time is not None and entry.timestamp < start_time:
                continue
            if end_time is not None and entry.timestamp > end_time:
                continue
            results.append(entry)
        return results

    def export(self, format: str = "json") -> str:
        with self._lock:
            entries = [entry.to_dict() for entry in self._entries]
        if format == "json":
            return json.dumps(entries, indent=2)
        raise ValueError(f"Unsupported export format: {format!r}")
