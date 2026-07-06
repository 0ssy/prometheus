from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DelegationRequest:
    request_id: str
    from_agent: str
    to_agent: str
    task: dict
    context: dict | None = None
    priority: int = 5


@dataclass
class DelegationResult:
    request_id: str
    success: bool
    result: dict | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
        }


class DelegationRouter:
    def __init__(self) -> None:
        self._chains: dict[str, list[str]] = {}
        self._lock = threading.RLock()

    def delegate(self, from_agent: str, to_agent: str, task: dict, context: dict | None = None) -> DelegationResult:
        request_id = str(uuid.uuid4())
        return DelegationResult(request_id=request_id, success=True, result={"delegated_to": to_agent})

    def can_delegate(self, from_agent: str, to_agent: str, task: dict) -> bool:
        return True

    def get_delegation_chain(self, task_id: str) -> list[str]:
        with self._lock:
            return list(self._chains.get(task_id, []))

    def route(self, task: dict, available_agents: list[str], capabilities: dict) -> str:
        return available_agents[0] if available_agents else ""

import threading
import uuid
