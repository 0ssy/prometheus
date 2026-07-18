"""Backend service for studio lifecycle management and cross-studio interoperability."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class StudioContract:
    """Cross-studio contract definition shared across studios."""

    studio_id: str
    action: str
    payload: Dict[str, Any] = field(default_factory=dict)
    response: Optional[Dict[str, Any]] = None


@dataclass
class StudioRuntime:
    """Runtime state for a launched studio."""

    studio_id: str
    definition: Dict[str, Any]
    status: str = "running"
    state: Dict[str, Any] = field(default_factory=dict)
    handlers: Dict[str, Callable[[StudioContract], Any]] = field(default_factory=dict)


class StudioService:
    """Manages studio lifecycle and cross-studio interoperability."""

    def __init__(self) -> None:
        self._studios: Dict[str, Dict[str, Any]] = {}
        self._runtimes: Dict[str, StudioRuntime] = {}
        self._lock = threading.Lock()
        self._contract_registry: Dict[str, Callable[[StudioContract], Any]] = {}

    def register_studio(self, definition: Dict[str, Any]) -> None:
        with self._lock:
            studio_id = definition.get("id")
            if not studio_id:
                raise ValueError("Studio definition must include an 'id'")
            self._studios[studio_id] = definition

    def get_studio(self, studio_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._studios.get(studio_id)

    def list_studios(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._studios)

    def launch_studio(self, studio_id: str) -> StudioRuntime:
        with self._lock:
            definition = self._studios.get(studio_id)
            if not definition:
                raise ValueError(f"Unknown studio: {studio_id}")
            if studio_id in self._runtimes:
                runtime = self._runtimes[studio_id]
                runtime.status = "running"
                return runtime
            runtime = StudioRuntime(studio_id=studio_id, definition=definition)
            self._runtimes[studio_id] = runtime
            return runtime

    def close_studio(self, studio_id: str) -> None:
        with self._lock:
            runtime = self._runtimes.get(studio_id)
            if runtime:
                runtime.status = "closed"

    def register_contract_handler(
        self,
        studio_id: str,
        action: str,
        handler: Callable[[StudioContract], Any],
    ) -> None:
        key = f"{studio_id}:{action}"
        self._contract_registry[key] = handler
        with self._lock:
            runtime = self._runtimes.get(studio_id)
            if runtime:
                runtime.handlers[action] = handler

    def send_contract(self, contract: StudioContract) -> Any:
        key = f"{contract.studio_id}:{contract.action}"
        handler = self._contract_registry.get(key)
        if not handler:
            raise ValueError(
                f"No contract handler registered for {contract.studio_id}:{contract.action}"
            )
        return handler(contract)

    def get_runtime(self, studio_id: str) -> Optional[StudioRuntime]:
        with self._lock:
            return self._runtimes.get(studio_id)
