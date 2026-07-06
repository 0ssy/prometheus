from __future__ import annotations

import enum
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from core.logger import get_logger

logger = get_logger(__name__)


class LifecycleState(enum.Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"
    DRAINING = "draining"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class LifecycleEvent:
    event_id: str
    state: LifecycleState
    timestamp: datetime
    details: str | None = None


class LifecycleManager:
    def __init__(self) -> None:
        self._state = LifecycleState.INITIALIZING
        self._history: list[LifecycleEvent] = []
        self._hooks: dict[str, list[object]] = {}
        self._lock = threading.RLock()

    def transition(self, new_state: LifecycleState, details: str | None = None) -> None:
        with self._lock:
            event = LifecycleEvent(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                state=new_state,
                timestamp=datetime.now(timezone.utc),
                details=details,
            )
            self._state = new_state
            self._history.append(event)
        logger.info(f"Lifecycle transition -> {new_state.value} ({details})")

    def get_state(self) -> LifecycleState:
        with self._lock:
            return self._state

    def get_history(self) -> list[LifecycleEvent]:
        with self._lock:
            return list(self._history)

    def register_hook(self, hook_name: str, callback: object) -> None:
        with self._lock:
            self._hooks.setdefault(hook_name, []).append(callback)
        logger.info(f"Registered lifecycle hook: {hook_name}")

    def execute_hooks(self, hook_name: str) -> None:
        with self._lock:
            callbacks = list(self._hooks.get(hook_name, []))
        for callback in callbacks:
            try:
                callback()
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Lifecycle hook {hook_name} failed: {exc}")

    def graceful_shutdown(self, timeout: int = 30) -> None:
        logger.info(f"Graceful shutdown requested (timeout={timeout}s)")
        self.transition(LifecycleState.DRAINING, details="graceful_shutdown")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(0.1)
        self.transition(LifecycleState.STOPPED, details="shutdown_complete")
        self.execute_hooks("on_shutdown")

    def hot_reload(self, component_name: str) -> bool:
        logger.info(f"Hot reload requested: {component_name}")
        self.execute_hooks(f"on_reload:{component_name}")
        return True
