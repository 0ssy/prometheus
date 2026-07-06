from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class KnowledgeDashboard:
    def get_graph_stats(self) -> dict[str, Any]:
        logger.debug("Computing knowledge graph stats")
        return {
            "nodes": 0,
            "edges": 0,
            "facts": 0,
        }

    def get_recent_facts(self, limit: int = 20) -> list[dict[str, Any]]:
        logger.debug("Fetching %d recent facts", limit)
        return []

    def get_learning_history(self, limit: int = 20) -> list[dict[str, Any]]:
        logger.debug("Fetching %d learning history entries", limit)
        return []
