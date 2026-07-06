from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ObservabilityStore:
    def __init__(self):
        self._metrics: dict[str, int] = defaultdict(int)
        self._traces: list[dict[str, Any]] = []
        self._event_history: list[dict[str, Any]] = []

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

    def snapshot(self) -> dict[str, Any]:
        return {
            "metrics": dict(self._metrics),
            "traces": list(self._traces),
            "event_history": list(self._event_history),
        }
