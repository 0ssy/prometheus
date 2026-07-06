"""
Prometheus Multi-Agent Coordination — Delegation
-------------------------------------------------
Routes tasks to the most suitable agent based on capability match and
current workload, and tracks delegation chains for accountability.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DelegationRequest:
    request_id: str
    from_agent: str
    to_agent: str
    task: str
    context: dict[str, Any] = field(default_factory=dict)
    priority: int = 5


@dataclass
class DelegationResult:
    request_id: str
    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None


class DelegationRouter:
    def __init__(self) -> None:
        self._chains: dict[str, list[str]] = {}
        self._counter = 0
        self._lock = threading.RLock()

    def can_delegate(self, from_agent: str, to_agent: str, task: str) -> bool:
        if not to_agent:
            return False
        if from_agent == to_agent:
            return False
        return True

    def delegate(
        self,
        from_agent: str,
        to_agent: str,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> DelegationResult:
        with self._lock:
            self._counter += 1
            request_id = f"del-{self._counter:04d}"
        if not self.can_delegate(from_agent, to_agent, task):
            logger.warning(f"Delegation blocked: {from_agent} -> {to_agent}")
            return DelegationResult(
                request_id=request_id,
                success=False,
                error="invalid delegation",
            )
        with self._lock:
            self._chains.setdefault(task, []).append(to_agent)
        logger.info(f"Delegated '{task}' from '{from_agent}' to '{to_agent}' ({request_id})")
        return DelegationResult(
            request_id=request_id,
            success=True,
            result={"from": from_agent, "to": to_agent, "task": task},
        )

    def get_delegation_chain(self, task_id: str) -> list[str]:
        with self._lock:
            return list(self._chains.get(task_id, []))

    def route(
        self,
        task: str,
        available_agents: list[str],
        capabilities: dict[str, Any],
    ) -> str:
        if not available_agents:
            logger.warning("No agents available for routing")
            return ""
        required = set(capabilities.get(task, []))
        best_agent = ""
        best_score = -1.0
        for agent in available_agents:
            agent_caps = set(capabilities.get(agent, []) if isinstance(capabilities.get(agent), list) else [])
            if required:
                score = len(required & agent_caps) / len(required)
            else:
                score = 0.5
            if score > best_score:
                best_score = score
                best_agent = agent
        logger.info(f"Routed task '{task}' to agent '{best_agent}' (score={best_score:.2f})")
        return best_agent
