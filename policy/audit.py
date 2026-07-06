from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import threading
import uuid

from core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class PolicyAuditEntry:
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = ""
    actor: str = ""
    action: str = ""
    resource: str = ""
    decision: bool = False
    matched_rules: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now()


class PolicyAuditLogger:
    def __init__(self) -> None:
        self._entries: list[PolicyAuditEntry] = []
        self._lock = threading.RLock()
        self._logger = get_logger(__name__)

    def log(self, entry: PolicyAuditEntry) -> None:
        with self._lock:
            self._entries.append(entry)
            self._logger.info(
                f"Audit: actor={entry.actor} action={entry.action} "
                f"resource={entry.resource} decision={entry.decision}"
            )

    def query(
        self,
        actor: str | None = None,
        action: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[PolicyAuditEntry]:
        with self._lock:
            results = list(self._entries)
            if actor is not None:
                results = [e for e in results if e.actor == actor]
            if action is not None:
                results = [e for e in results if e.action == action]
            if start_time is not None:
                results = [e for e in results if e.timestamp >= start_time]
            if end_time is not None:
                results = [e for e in results if e.timestamp <= end_time]
            return results

    def export(self, format: str = "json") -> str:
        import json

        with self._lock:
            data = [
                {
                    "entry_id": e.entry_id,
                    "timestamp": e.timestamp,
                    "actor": e.actor,
                    "action": e.action,
                    "resource": e.resource,
                    "decision": e.decision,
                    "matched_rules": e.matched_rules,
                    "metadata": e.metadata,
                }
                for e in self._entries
            ]
            if format == "json":
                return json.dumps(data, indent=2)
            raise ValueError(f"Unsupported export format: {format}")


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
