from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class PluginsDashboard:
    def list_plugins(self) -> list[dict[str, Any]]:
        logger.debug("Listing plugins")
        return []

    def get_plugin_details(self, plugin_name: str) -> dict[str, Any]:
        logger.debug("Fetching details for plugin %s", plugin_name)
        return {
            "plugin_name": plugin_name,
            "found": False,
        }
