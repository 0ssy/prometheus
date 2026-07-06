from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class KnowledgeDashboard:
    def get_graph_stats(self) -> dict[str, Any]:
        return {"nodes": 0, "edges": 0}

    def get_recent_facts(self, limit: int = 20) -> list[dict[str, Any]]:
        return []

    def get_learning_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return []
