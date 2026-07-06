from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LifecycleManager:
    def __init__(self):
        self.started_at: datetime | None = None
        self.stopped_at: datetime | None = None
        self._shutdown_hooks: list[Callable[[], None]] = []

    def mark_started(self) -> None:
        self.started_at = _utc_now()
        self.stopped_at = None

    def register_shutdown_hook(self, hook: Callable[[], None]) -> None:
        self._shutdown_hooks.append(hook)

    def shutdown(self) -> None:
        for hook in self._shutdown_hooks:
            hook()
        self.stopped_at = _utc_now()

    def status(self) -> dict:
        return {
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "running": self.started_at is not None and self.stopped_at is None,
        }
