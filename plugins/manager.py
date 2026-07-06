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
from api.plugin_api import PluginApi
from core.logger import get_logger

logger = get_logger(__name__)


class PluginManager(PluginApi):
    def __init__(self):
        self._plugins: dict[str, PrometheusPlugin] = {}

    def register(self, plugin: PrometheusPlugin) -> None:
        if plugin.name in self._plugins:
            logger.warning(f"Plugin '{plugin.name}' already registered — overwriting")
        plugin.on_load()
        self._plugins[plugin.name] = plugin
        logger.info(f"Loaded plugin: {plugin.name} v{plugin.version}")

    def get(self, name: str) -> PrometheusPlugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict]:
        return [{"name": p.name, "version": p.version} for p in self._plugins.values()]

    def run(self, name: str, context: dict) -> dict:
        plugin = self.get(name)
        if plugin is None:
            raise ValueError(f"No such plugin: {name}")
        return plugin.run(context)


plugin_manager = PluginManager()
