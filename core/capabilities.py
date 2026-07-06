from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from api.events import CapabilityExecutedEvent
from contracts.capability import CapabilityApi
from contracts.event_bus import EventBus
from core.logger import get_logger

logger = get_logger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CapabilityDefinition:
    name: str
    target: str
    description: str
    permissions: set[str]
    executor: Callable[[dict[str, Any]], Any]


@dataclass
class CapabilityExecutionRecord:
    timestamp: datetime
    capability_name: str
    payload: dict[str, Any]
    granted_permissions: list[str]
    success: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "capability_name": self.capability_name,
            "payload": self.payload,
            "granted_permissions": self.granted_permissions,
            "success": self.success,
            "error": self.error,
        }


class CapabilityManager(CapabilityApi):
    def __init__(self, event_bus: EventBus | None = None):
        self._event_bus = event_bus
        self._capabilities: dict[str, CapabilityDefinition] = {}
        self._history: list[CapabilityExecutionRecord] = []

    def register(
        self,
        name: str,
        target: str,
        description: str,
        permissions: set[str],
        executor: Callable[[dict[str, Any]], Any],
    ) -> None:
        if name in self._capabilities:
            raise ValueError(f"Capability '{name}' is already registered")
        self._capabilities[name] = CapabilityDefinition(
            name=name,
            target=target,
            description=description,
            permissions=set(permissions),
            executor=executor,
        )
        logger.info("Registered capability: %s (target=%s)", name, target)

    def exists(self, name: str) -> bool:
        return name in self._capabilities

    def discover(
        self, prefix: str | None = None, target: str | None = None
    ) -> list[dict[str, Any]]:
        matches = []
        for capability in self._capabilities.values():
            if prefix and not capability.name.startswith(prefix):
                continue
            if target and capability.target != target:
                continue
            matches.append(
                {
                    "name": capability.name,
                    "target": capability.target,
                    "description": capability.description,
                    "permissions": sorted(capability.permissions),
                }
            )
        matches.sort(key=lambda capability: capability["name"])
        return matches

    def authorize(self, name: str, granted_permissions: set[str]) -> bool:
        capability = self._require(name)
        return capability.permissions.issubset(granted_permissions)

    def execute(
        self,
        name: str,
        payload: dict[str, Any],
        granted_permissions: set[str],
    ) -> Any:
        capability = self._require(name)
        missing = capability.permissions - granted_permissions
        if missing:
            error = (
                f"Permission denied for capability '{name}'. "
                f"Missing permissions: {sorted(missing)}"
            )
            self._record(
                name=name,
                payload=payload,
                granted_permissions=granted_permissions,
                success=False,
                error=error,
            )
            self._publish_result(name, success=False)
            raise PermissionError(error)

        try:
            result = capability.executor(payload)
        except Exception as exc:
            self._record(
                name=name,
                payload=payload,
                granted_permissions=granted_permissions,
                success=False,
                error=str(exc),
            )
            self._publish_result(name, success=False)
            raise

        self._record(
            name=name,
            payload=payload,
            granted_permissions=granted_permissions,
            success=True,
            error=None,
        )
        self._publish_result(name, success=True)
        return result

    def history(self, capability_name: str | None = None) -> list[dict[str, Any]]:
        records = self._history
        if capability_name:
            records = [record for record in records if record.capability_name == capability_name]
        return [record.to_dict() for record in records]

    def _require(self, name: str) -> CapabilityDefinition:
        capability = self._capabilities.get(name)
        if capability is None:
            raise ValueError(f"No such capability: {name}")
        return capability

    def _record(
        self,
        name: str,
        payload: dict[str, Any],
        granted_permissions: set[str],
        success: bool,
        error: str | None,
    ) -> None:
        self._history.append(
            CapabilityExecutionRecord(
                timestamp=_utc_now(),
                capability_name=name,
                payload=dict(payload),
                granted_permissions=sorted(granted_permissions),
                success=success,
                error=error,
            )
        )

    def _publish_result(self, name: str, success: bool) -> None:
        if self._event_bus is None:
            return
        self._event_bus.publish(
            CapabilityExecutedEvent(capability_name=name, success=success)
        )
