"""
Prometheus Plugin Manager
-----------------------------------------
Discovers plugin classes and keeps a registry. Phase Alpha loads
plugins that are Python classes registered directly (see
plugins/installed/echo_plugin.py for the reference example) —
dynamic filesystem discovery of arbitrary third-party plugins is a
Phase Beta/Gamma concern once there's a security model for it.
"""

from .base import PrometheusPlugin
from contracts.plugin import PluginApi
from contracts.event_bus import EventBus
from contracts.versioning import CONTRACT_VERSION, validate_contract_compatibility
from api.events import PluginRanEvent, PluginErrorEvent
from core.logger import get_logger
from core.event_bus import event_bus as default_event_bus

import concurrent.futures

logger = get_logger(__name__)


class PluginManager(PluginApi):
    def __init__(self, event_bus: EventBus | None = None):
        self._plugins: dict[str, PrometheusPlugin] = {}
        self._event_bus = event_bus or default_event_bus

    def register(self, plugin: PrometheusPlugin) -> None:
        if plugin.name in self._plugins:
            logger.warning(f"Plugin '{plugin.name}' already registered — overwriting")
        validate_contract_compatibility(plugin.required_contract_version, CONTRACT_VERSION)
        plugin.on_load()
        self._plugins[plugin.name] = plugin
        logger.info(f"Loaded plugin: {plugin.name} v{plugin.version}")

    def get(self, name: str) -> PrometheusPlugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict]:
        return [{"name": p.name, "version": p.version} for p in self._plugins.values()]

    def run(self, name: str, context: dict, timeout: float | None = None) -> dict:
        plugin = self.get(name)
        if plugin is None:
            raise ValueError(f"No such plugin: {name}")
        try:
            if timeout is not None and timeout > 0:
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                try:
                    future = executor.submit(plugin.run, context)
                    try:
                        result = future.result(timeout=timeout)
                    except concurrent.futures.TimeoutError:
                        logger.warning("Plugin '%s' timed out after %.2fs; aborting", name, timeout)
                        self._event_bus.publish(
                            PluginErrorEvent(plugin_name=name, error="timeout")
                        )
                        return {"error": "timeout"}
                finally:
                    executor.shutdown(wait=False)
            else:
                result = plugin.run(context)
        except Exception as exc:
            logger.exception("Plugin '%s' raised an error", name)
            self._event_bus.publish(
                PluginErrorEvent(plugin_name=name, error=str(exc))
            )
            return {"error": str(exc)}
        self._event_bus.publish(PluginRanEvent(plugin_name=name, result=result))
        return result


plugin_manager = PluginManager()
