from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from core.logger import get_logger

logger = get_logger(__name__)


class LifecycleState(str, Enum):
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
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, Any] = field(default_factory=dict)


class LifecycleManager:
    def __init__(self) -> None:
        self._state = LifecycleState.INITIALIZING
        self._history: list[LifecycleEvent] = []
        self._hooks: dict[str, list[Callable]] = {}
        self._lock = threading.RLock()

    def transition(self, new_state: LifecycleState, details: dict[str, Any] | None = None) -> None:
        with self._lock:
            old_state = self._state
            self._state = new_state
            event = LifecycleEvent(
                event_id=str(uuid.uuid4()),
                state=new_state,
                details=details or {"from": old_state.value},
            )
            self._history.append(event)
            logger.info("Lifecycle transition: %s -> %s", old_state.value, new_state.value)
            self.execute_hooks("on_transition")

    def get_state(self) -> LifecycleState:
        with self._lock:
            return self._state

    def get_history(self) -> list[LifecycleEvent]:
        with self._lock:
            return list(self._history)

    def register_hook(self, hook_name: str, callback: Callable) -> None:
        with self._lock:
            self._hooks.setdefault(hook_name, []).append(callback)

    def execute_hooks(self, hook_name: str) -> None:
        with self._lock:
            hooks = list(self._hooks.get(hook_name, []))
        for hook in hooks:
            try:
                hook()
            except Exception:
                logger.exception("Hook %s failed", hook_name)

    def graceful_shutdown(self, timeout: int = 30) -> None:
        self.transition(LifecycleState.DRAINING, {"timeout": timeout})
        self.execute_hooks("on_shutdown")
        self.transition(LifecycleState.STOPPED)

    def hot_reload(self, component_name: str) -> bool:
        logger.info("Hot reload requested for: %s", component_name)
        return True


import threading
import uuid
