from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.logger import get_logger


class NodeStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    SYNCING = "syncing"


@dataclass
class NodeInfo:
    node_id: str
    name: str
    host: str
    port: int
    capabilities: list[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.ONLINE
    last_heartbeat: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class NodeRegistry:
    def __init__(self) -> None:
        self._nodes: dict[str, NodeInfo] = {}
        self._lock = threading.Lock()
        self._logger = get_logger(__name__)

    def register(self, node_info: NodeInfo) -> None:
        with self._lock:
            self._nodes[node_info.node_id] = node_info
            self._logger.info("registered node %s (%s:%d)", node_info.node_id, node_info.host, node_info.port)

    def unregister(self, node_id: str) -> bool:
        with self._lock:
            if node_id in self._nodes:
                del self._nodes[node_id]
                self._logger.info("unregistered node %s", node_id)
                return True
            return False

    def get(self, node_id: str) -> NodeInfo | None:
        with self._lock:
            return self._nodes.get(node_id)

    def list_online(self) -> list[NodeInfo]:
        with self._lock:
            return [node for node in self._nodes.values() if node.status == NodeStatus.ONLINE]

    def heartbeat(self, node_id: str) -> bool:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.last_heartbeat = time.time()
            if node.status != NodeStatus.ONLINE:
                node.status = NodeStatus.ONLINE
                self._logger.info("node %s recovered to ONLINE", node_id)
            return True

    def find_by_capability(self, capability: str) -> list[NodeInfo]:
        with self._lock:
            return [node for node in self._nodes.values() if capability in node.capabilities and node.status == NodeStatus.ONLINE]
