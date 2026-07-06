from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class NodeStatus(str, Enum):
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
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


class NodeRegistry:
    def __init__(self) -> None:
        self._nodes: dict[str, NodeInfo] = {}
        self._lock = threading.RLock()

    def register(self, node_info: NodeInfo) -> None:
        with self._lock:
            self._nodes[node_info.node_id] = node_info
            logger.info("Registered node: %s", node_info.node_id)

    def unregister(self, node_id: str) -> bool:
        with self._lock:
            if node_id in self._nodes:
                del self._nodes[node_id]
                return True
            return False

    def get(self, node_id: str) -> NodeInfo | None:
        with self._lock:
            return self._nodes.get(node_id)

    def list_online(self) -> list[NodeInfo]:
        with self._lock:
            return [n for n in self._nodes.values() if n.status == NodeStatus.ONLINE]

    def heartbeat(self, node_id: str) -> bool:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.last_heartbeat = datetime.now(timezone.utc)
            node.status = NodeStatus.ONLINE
            return True

    def find_by_capability(self, capability: str) -> list[NodeInfo]:
        with self._lock:
            return [n for n in self._nodes.values() if capability in n.capabilities]


import threading
