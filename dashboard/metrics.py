from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class MetricsDashboard:
    def get_metrics(self) -> dict[str, Any]:
        logger.debug("Fetching metrics")
        return {}

    def get_metric_history(
        self, metric_name: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        logger.debug("Fetching history for metric %s (limit=%d)", metric_name, limit)
        return []

    def get_system_metrics(self) -> dict[str, Any]:
        logger.debug("Fetching system metrics")
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_percent": 0.0,
        }
