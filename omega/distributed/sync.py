from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class SyncDirection(str, Enum):
    PUSH = "push"
    PULL = "pull"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class KnowledgeSync:
    source_node: str
    target_node: str
    last_sync: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    direction: SyncDirection = SyncDirection.PUSH
    entries_synced: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_node": self.source_node,
            "target_node": self.target_node,
            "last_sync": self.last_sync.isoformat(),
            "direction": self.direction.value,
            "entries_synced": self.entries_synced,
        }


class KnowledgeSynchronizer:
    def __init__(self) -> None:
        self._pending: dict[str, list[dict]] = {}
        self._completed: list[KnowledgeSync] = []

    def sync(self, source_node: str, target_node: str, direction: SyncDirection = SyncDirection.PUSH) -> KnowledgeSync:
        sync_record = KnowledgeSync(source_node=source_node, target_node=target_node, direction=direction)
        self._completed.append(sync_record)
        return sync_record

    def get_pending_changes(self, node_id: str) -> list[dict[str, Any]]:
        return self._pending.get(node_id, [])

    def mark_synced(self, sync_id: str) -> None:
        pass


class CapabilitySynchronizer:
    def __init__(self) -> None:
        self._remote_capabilities: dict[str, list[dict]] = {}

    def sync_capabilities(self, source_node: str, target_node: str) -> dict[str, Any]:
        return {"source": source_node, "target": target_node, "synced": 0}

    def register_remote_capability(self, node_id: str, capability: dict[str, Any]) -> None:
        self._remote_capabilities.setdefault(node_id, []).append(capability)
