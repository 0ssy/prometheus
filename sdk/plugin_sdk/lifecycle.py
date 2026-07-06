from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from core.logger import get_logger

from .interfaces import BasePlugin, PluginContext, PluginResult

logger = get_logger(__name__)


class PluginLifecycle(Enum):
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    READY = "ready"
    EXECUTING = "executing"
    SHUTTING_DOWN = "shutting_down"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginState:
    plugin_id: str
    lifecycle: PluginLifecycle = PluginLifecycle.REGISTERED
    last_error: str | None = None
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_executed: datetime | None = None


class PluginLifecycleError(Exception):
    pass


class PluginLifecycleManager:
    def __init__(self) -> None:
        self._instances: dict[str, BasePlugin] = {}
        self._states: dict[str, PluginState] = {}
        self._disabled: set[str] = set()
        self._context: PluginContext | None = None

    def set_context(self, context: PluginContext) -> None:
        self._context = context

    def register(self, plugin_id: str, plugin: BasePlugin) -> PluginState:
        if plugin_id in self._instances:
            raise PluginLifecycleError(f"Plugin '{plugin_id}' is already registered")
        self._instances[plugin_id] = plugin
        state = PluginState(plugin_id=plugin_id, lifecycle=PluginLifecycle.REGISTERED)
        self._states[plugin_id] = state
        logger.info("Registered plugin: %s", plugin_id)
        return state

    def initialize(self, plugin_id: str) -> PluginState:
        state = self._require_state(plugin_id)
        if state.lifecycle in (PluginLifecycle.DISABLED, PluginLifecycle.ERROR):
            raise PluginLifecycleError(f"Cannot initialize plugin '{plugin_id}' in state {state.lifecycle.value}")
        plugin = self._instances[plugin_id]
        state.lifecycle = PluginLifecycle.INITIALIZING
        try:
            plugin.initialize(self._context)
            state.lifecycle = PluginLifecycle.READY
            state.last_error = None
            logger.info("Initialized plugin: %s", plugin_id)
        except Exception as exc:
            state.lifecycle = PluginLifecycle.ERROR
            state.last_error = str(exc)
            logger.exception("Failed to initialize plugin %s", plugin_id)
            raise PluginLifecycleError(str(exc)) from exc
        return state

    def execute(self, plugin_id: str, payload: dict[str, Any]) -> PluginResult:
        state = self._require_state(plugin_id)
        if plugin_id in self._disabled:
            raise PluginLifecycleError(f"Plugin '{plugin_id}' is disabled")
        if state.lifecycle not in (PluginLifecycle.READY, PluginLifecycle.EXECUTING):
            raise PluginLifecycleError(f"Plugin '{plugin_id}' is not ready (state={state.lifecycle.value})")
        plugin = self._instances[plugin_id]
        state.lifecycle = PluginLifecycle.EXECUTING
        try:
            result = plugin.execute(payload)
            state.lifecycle = PluginLifecycle.READY
            state.last_executed = datetime.now(timezone.utc)
            state.last_error = None if result.success else result.error
            return result
        except Exception as exc:
            state.lifecycle = PluginLifecycle.ERROR
            state.last_error = str(exc)
            logger.exception("Plugin %s raised during execute", plugin_id)
            return PluginResult.fail(str(exc))

    def shutdown(self, plugin_id: str) -> PluginState:
        state = self._require_state(plugin_id)
        plugin = self._instances[plugin_id]
        state.lifecycle = PluginLifecycle.SHUTTING_DOWN
        try:
            plugin.shutdown()
            state.lifecycle = PluginLifecycle.REGISTERED
            logger.info("Shut down plugin: %s", plugin_id)
        except Exception as exc:
            state.lifecycle = PluginLifecycle.ERROR
            state.last_error = str(exc)
            logger.exception("Error shutting down plugin %s", plugin_id)
            raise PluginLifecycleError(str(exc)) from exc
        return state

    def disable(self, plugin_id: str) -> PluginState:
        state = self._require_state(plugin_id)
        self._disabled.add(plugin_id)
        state.lifecycle = PluginLifecycle.DISABLED
        logger.info("Disabled plugin: %s", plugin_id)
        return state

    def enable(self, plugin_id: str) -> PluginState:
        state = self._require_state(plugin_id)
        self._disabled.discard(plugin_id)
        state.lifecycle = PluginLifecycle.REGISTERED
        logger.info("Enabled plugin: %s", plugin_id)
        return state

    def get_state(self, plugin_id: str) -> PluginState:
        return self._require_state(plugin_id)

    def list_states(self) -> list[PluginState]:
        return list(self._states.values())

    def _require_state(self, plugin_id: str) -> PluginState:
        state = self._states.get(plugin_id)
        if state is None:
            raise PluginLifecycleError(f"No such plugin: {plugin_id}")
        return state
