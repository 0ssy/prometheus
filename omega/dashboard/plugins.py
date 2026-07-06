from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class PluginsDashboard:
    def list_plugins(self) -> list[dict[str, Any]]:
        return []

    def get_plugin_details(self, plugin_name: str) -> dict[str, Any]:
        return {"plugin": plugin_name, "details": {}}
