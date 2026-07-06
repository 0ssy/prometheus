from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class MetricsDashboard:
    def get_metrics(self) -> dict[str, Any]:
        return {"metrics": {}}

    def get_metric_history(self, metric_name: str, limit: int = 100) -> list[dict[str, Any]]:
        return []

    def get_system_metrics(self) -> dict[str, Any]:
        return {"cpu": 0.0, "memory": 0.0, "disk": 0.0}
