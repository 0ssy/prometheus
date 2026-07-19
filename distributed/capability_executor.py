from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class DistributedCapabilityExecutor:
    def execute_on_node(
        self,
        node_id: str,
        capability_name: str,
        payload: dict[str, Any],
        granted_permissions: set[str],
    ) -> dict[str, Any]:
        return {
            "node_id": node_id,
            "capability": capability_name,
            "result": None,
            "status": "stub",
        }

    def broadcast_capability(
        self,
        capability_name: str,
        payload: dict[str, Any],
        granted_permissions: set[str],
    ) -> list[dict[str, Any]]:
        return []
