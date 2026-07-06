from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from core.logger import get_logger

logger = get_logger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str
    author: str
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    entrypoint: str = ""


@dataclass
class PluginContext:
    kernel: Any
    capability_manager: Any
    knowledge_engine: Any
    event_bus: Any
    logger: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginResult:
    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Any = None, **metadata: Any) -> PluginResult:
        return cls(success=True, data=data, metadata=dict(metadata))

    @classmethod
    def fail(cls, error: str, data: Any = None, **metadata: Any) -> PluginResult:
        return cls(success=False, data=data, error=error, metadata=dict(metadata))


@dataclass
class PluginCapability:
    name: str
    description: str
    permissions: set[str] = field(default_factory=set)
    executor: Callable[..., Any] | None = None


class BasePlugin:
    manifest: PluginManifest

    def initialize(self, context: PluginContext) -> None:
        logger.debug("Initializing plugin %s", getattr(self.manifest, "name", self.__class__.__name__))

    def execute(self, payload: dict[str, Any]) -> PluginResult:
        capability_name = payload.get("capability") if isinstance(payload, dict) else None
        if not capability_name:
            return PluginResult.fail("No 'capability' specified in payload")
        method = getattr(self, capability_name, None)
        if method is None or not callable(method):
            return PluginResult.fail(f"No such capability: {capability_name}")
        kwargs = {k: v for k, v in payload.items() if k != "capability"}
        try:
            data = method(**kwargs)
        except Exception as exc:
            return PluginResult.fail(str(exc))
        if isinstance(data, PluginResult):
            return data
        return PluginResult.ok(data)

    def shutdown(self) -> None:
        logger.debug("Shutting down plugin %s", getattr(self.manifest, "name", self.__class__.__name__))

    def health(self) -> dict[str, Any]:
        return {
            "plugin": getattr(self.manifest, "name", self.__class__.__name__),
            "status": "healthy",
            "timestamp": _utc_now().isoformat(),
        }
