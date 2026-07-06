from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class LogsDashboard:
    def get_recent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        return []

    def get_logs_by_level(self, level: str, limit: int = 50) -> list[dict[str, Any]]:
        return []

    def search_logs(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        return []
