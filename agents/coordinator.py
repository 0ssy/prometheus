"""
Prometheus Multi-Agent Coordination — Coordinator
-------------------------------------------------
Task lifecycle management for coordinating work across multiple agents.
Tracks submissions, assignments, execution state, and per-agent workload.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentTask:
    task_id: str
    description: str
    required_capabilities: set[str] = field(default_factory=set)
    priority: int = 5
    assigned_agent: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    result: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "required_capabilities": list(self.required_capabilities),
            "priority": self.priority,
            "assigned_agent": self.assigned_agent,
            "status": self.status.value,
            "result": self.result,
            "created_at": self.created_at.isoformat(),
        }


class AgentCoordinator:
    def __init__(self) -> None:
        self._tasks: dict[str, AgentTask] = {}
        self._lock = threading.RLock()
        self._counter = 0

    def submit_task(
        self,
        description: str,
        required_capabilities: set[str] | None = None,
        priority: int = 5,
    ) -> AgentTask:
        with self._lock:
            self._counter += 1
            task_id = f"task-{self._counter:04d}"
            task = AgentTask(
                task_id=task_id,
                description=description,
                required_capabilities=set(required_capabilities or set()),
                priority=priority,
                status=TaskStatus.PENDING,
            )
            self._tasks[task_id] = task
        logger.info(f"Submitted task {task_id}: {description} (priority={priority})")
        return task

    def assign_agent(self, task_id: str, agent_name: str) -> AgentTask:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"No such task: {task_id}")
            if task.status not in (TaskStatus.PENDING, TaskStatus.ASSIGNED):
                raise ValueError(f"Task {task_id} cannot be assigned in state {task.status.value}")
            task.assigned_agent = agent_name
            task.status = TaskStatus.ASSIGNED
        logger.info(f"Assigned task {task_id} to agent '{agent_name}'")
        return task

    def run_task(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"No such task: {task_id}")
            if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                logger.warning(f"Task {task_id} already in terminal state {task.status.value}")
                return task.result or {"status": task.status.value}
            if task.assigned_agent is None:
                raise ValueError(f"Task {task_id} has no assigned agent")
            previous = task.status
            task.status = TaskStatus.RUNNING

        logger.info(f"Running task {task_id} on agent '{task.assigned_agent}'")
        try:
            result = {
                "task_id": task_id,
                "agent": task.assigned_agent,
                "status": "completed",
                "output": f"executed: {task.description}",
            }
            with self._lock:
                task.result = result
                task.status = TaskStatus.COMPLETED
        except Exception as exc:  # pragma: no cover - defensive
            with self._lock:
                task.status = TaskStatus.FAILED
                task.result = {"error": str(exc)}
            logger.exception(f"Task {task_id} failed: {exc}")
            result = task.result
        return result

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                logger.warning(f"Cannot cancel unknown task {task_id}")
                return False
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                logger.warning(f"Cannot cancel task {task_id} in state {task.status.value}")
                return False
            task.status = TaskStatus.CANCELLED
        logger.info(f"Cancelled task {task_id}")
        return True

    def get_task(self, task_id: str) -> AgentTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self, status: TaskStatus | None = None) -> list[AgentTask]:
        with self._lock:
            tasks = list(self._tasks.values())
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: (-t.priority, t.created_at))

    def get_agent_workload(self, agent_name: str) -> int:
        with self._lock:
            return sum(
                1
                for t in self._tasks.values()
                if t.assigned_agent == agent_name
                and t.status in (TaskStatus.ASSIGNED, TaskStatus.RUNNING)
            )

    def coordinate(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        logger.info(f"Coordinating batch of {len(tasks)} tasks")
        submitted: list[str] = []
        results: dict[str, Any] = {}
        for spec in tasks:
            description = spec.get("description", "")
            capabilities = set(spec.get("required_capabilities", []) or [])
            priority = int(spec.get("priority", 5))
            task = self.submit_task(description, capabilities, priority)
            submitted.append(task.task_id)
            agent_name = spec.get("agent") or spec.get("assigned_agent")
            if agent_name:
                self.assign_agent(task.task_id, agent_name)
                results[task.task_id] = self.run_task(task.task_id)
        return {
            "submitted": submitted,
            "results": results,
            "count": len(submitted),
        }
