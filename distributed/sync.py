from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.logger import get_logger
from distributed.crdt import CrdtNode


class SyncDirection(Enum):
    PUSH = "push"
    PULL = "pull"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class KnowledgeSync:
    source_node: str
    target_node: str
    last_sync: float
    direction: SyncDirection
    entries_synced: int = 0


class KnowledgeSynchronizer:
    def __init__(self) -> None:
        self._syncs: dict[str, KnowledgeSync] = {}
        self._pending: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.Lock()
        self._logger = get_logger(__name__)
        self._sync_counter = 0
        self._nodes: dict[str, CrdtNode] = {}

    def sync(self, source_node: str, target_node: str, direction: SyncDirection = SyncDirection.PUSH) -> KnowledgeSync:
        with self._lock:
            sync_id = f"sync-{self._sync_counter}"
            self._sync_counter += 1
            knowledge_sync = KnowledgeSync(
                source_node=source_node,
                target_node=target_node,
                last_sync=time.time(),
                direction=direction,
                entries_synced=0,
            )
            self._syncs[sync_id] = knowledge_sync
            self._logger.info("sync %s: %s -> %s (%s)", sync_id, source_node, target_node, direction.value)
            return knowledge_sync

    def register_node(self, node_id: str) -> CrdtNode:
        with self._lock:
            if node_id not in self._nodes:
                self._nodes[node_id] = CrdtNode(node_id=node_id)
            return self._nodes[node_id]

    def merge_nodes(self, source_node_id: str, target_node_id: str) -> CrdtNode | None:
        with self._lock:
            source = self._nodes.get(source_node_id)
            target = self._nodes.get(target_node_id)
            if source is None or target is None:
                return None
            merged = target.merge(source)
            self._nodes[target_node_id] = merged
            return merged

    def get_node_state(self, node_id: str) -> dict[str, Any] | None:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return None
            return node.to_dict()

    def apply_remote_state(self, node_id: str, state: dict[str, Any]) -> CrdtNode | None:
        with self._lock:
            remote = CrdtNode.from_dict(state)
            local = self._nodes.get(node_id)
            if local is None:
                self._nodes[node_id] = remote
                return remote
            merged = local.merge(remote)
            self._nodes[node_id] = merged
            return merged

    def get_pending_changes(self, node_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._pending.get(node_id, []))

    def mark_synced(self, sync_id: str) -> None:
        with self._lock:
            knowledge_sync = self._syncs.get(sync_id)
            if knowledge_sync:
                knowledge_sync.entries_synced += 1
                self._logger.debug("marked synced: %s", sync_id)


class CapabilitySynchronizer:
    def __init__(self) -> None:
        self._capabilities: dict[str, set[str]] = {}
        self._lock = threading.Lock()
        self._logger = get_logger(__name__)

    def sync_capabilities(self, source_node: str, target_node: str) -> dict[str, Any]:
        with self._lock:
            source_caps = self._capabilities.get(source_node, set())
            target_caps = self._capabilities.get(target_node, set())
            new_caps = source_caps - target_caps
            self._logger.info("cap sync %s -> %s: %d new capabilities", source_node, target_node, len(new_caps))
            return {"new_capabilities": list(new_caps), "source": source_node, "target": target_node}

    def register_remote_capability(self, node_id: str, capability: str) -> None:
        with self._lock:
            if node_id not in self._capabilities:
                self._capabilities[node_id] = set()
            self._capabilities[node_id].add(capability)
            self._logger.debug("registered remote capability %s for %s", capability, node_id)
