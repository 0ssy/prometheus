from __future__ import annotations

import time
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

    def snapshot(self, status: dict[str, Any] | None = None) -> dict[str, Any]:
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
        return {
            "metrics": dict(self._metrics),
            "traces": list(self._traces),
            "event_history": list(self._event_history),
            "events_per_sec": round(self._rate_per_sec(list(self._event_timestamps)), 2),
            "commands_per_sec": round(self._rate_per_sec(list(self._command_timestamps)), 2),
            "subsystems": subsystems,
        }
