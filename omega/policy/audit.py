from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PolicyAuditEntry:
    entry_id: str
    timestamp: datetime
    actor: str
    action: str
    resource: str
    decision: str
    matched_rules: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "action": self.action,
            "resource": self.resource,
            "decision": self.decision,
            "matched_rules": self.matched_rules,
            "metadata": self.metadata,
        }


class PolicyAuditLogger:
    def __init__(self) -> None:
        self._entries: list[PolicyAuditEntry] = []
        self._lock = Lock()

    def log(self, entry: PolicyAuditEntry) -> None:
        with self._lock:
            self._entries.append(entry)

    def record(self, actor: str, action: str, resource: str, decision: str, matched_rules: list[str] | None = None, metadata: dict[str, Any] | None = None) -> PolicyAuditEntry:
        entry = PolicyAuditEntry(
            entry_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            actor=actor,
            action=action,
            resource=resource,
            decision=decision,
            matched_rules=matched_rules or [],
            metadata=dict(metadata or {}),
        )
        self.log(entry)
        return entry

    def query(self, actor: str | None = None, action: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None) -> list[PolicyAuditEntry]:
        with self._lock:
            entries = list(self._entries)
        results = []
        for entry in entries:
            if actor is not None and entry.actor != actor:
                continue
            if action is not None and entry.action != action:
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
            import json
            return json.dumps(entries, indent=2)
        raise ValueError(f"Unsupported export format: {format!r}")


import uuid
