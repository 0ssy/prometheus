from __future__ import annotations

import threading
from typing import Any

from core.logger import get_logger
from distributed.node import NodeInfo, NodeRegistry


class DistributedRuntime:
    def __init__(self) -> None:
        self._registry = NodeRegistry()
        self._lock = threading.Lock()
        self._logger = get_logger(__name__)
        self._local_node_id: str | None = None

    def register_node(self, node_id: str, host: str, port: int, capabilities: list[str]) -> NodeInfo:
        node_info = NodeInfo(
            node_id=node_id,
            name=node_id,
            host=host,
            port=port,
            capabilities=capabilities,
        )
        self._registry.register(node_info)
        return node_info

    def unregister_node(self, node_id: str) -> bool:
        return self._registry.unregister(node_id)

    def broadcast(self, event_type: str, payload: dict[str, Any]) -> list[str]:
        online_nodes = self._registry.list_online()
        recipients: list[str] = []
        for node in online_nodes:
            self._logger.info("broadcast %s to %s", event_type, node.node_id)
            recipients.append(node.node_id)
        return recipients

    def sync_knowledge(self, source_node_id: str, target_node_id: str) -> dict:
        source = self._registry.get(source_node_id)
        target = self._registry.get(target_node_id)
        if source is None or target is None:
            self._logger.warning("sync failed: source=%s, target=%s", source_node_id, target_node_id)
            return {"status": "error", "entries_synced": 0}
        with self._lock:
            self._logger.info("syncing knowledge %s -> %s", source_node_id, target_node_id)
            return {"status": "ok", "source": source_node_id, "target": target_node_id, "entries_synced": 0}

    def get_cluster_status(self) -> dict[str, Any]:
        online = self._registry.list_online()
        return {
            "total_nodes": len(online),
            "nodes": [node.node_id for node in online],
            "leader": self.elect_leader(),
        }

    def elect_leader(self) -> str | None:
        online = self._registry.list_online()
        if not online:
            return None
        leader = min(online, key=lambda n: n.node_id)
        self._logger.info("elected leader: %s", leader.node_id)
        return leader.node_id
