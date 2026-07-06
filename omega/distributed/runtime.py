from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger

from omega.distributed.node import NodeRegistry, NodeInfo, NodeStatus

logger = get_logger(__name__)


class DistributedRuntime:
    def __init__(self) -> None:
        self._registry = NodeRegistry()
        self._leader: str | None = None

    def register_node(self, node_id: str, host: str, port: int, capabilities: list[str]) -> NodeInfo:
        node = NodeInfo(node_id=node_id, name=node_id, host=host, port=port, capabilities=capabilities)
        self._registry.register(node)
        return node

    def unregister_node(self, node_id: str) -> bool:
        return self._registry.unregister(node_id)

    def broadcast(self, event_type: str, payload: dict[str, Any]) -> list[str]:
        nodes = self._registry.list_online()
        return [n.node_id for n in nodes]

    def sync_knowledge(self, source_node_id: str, target_node_id: str) -> dict[str, Any]:
        return {"source": source_node_id, "target": target_node_id, "entries_synced": 0}

    def get_cluster_status(self) -> dict[str, Any]:
        nodes = self._registry.list_online()
        return {"online_nodes": len(nodes), "nodes": [n.node_id for n in nodes]}

    def elect_leader(self) -> str | None:
        nodes = self._registry.list_online()
        if not nodes:
            return None
        self._leader = nodes[0].node_id
        return self._leader
