from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import threading
import uuid

from core.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
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
    result: dict | None = None
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

    def coordinate(self, tasks: list[dict]) -> dict[str, Any]:
        results = []
        for task_spec in tasks:
            task = self._create_task(task_spec)
            results.append(task.to_dict())
        return {"results": results}

    def _create_task(self, task_spec: dict) -> AgentTask:
        task_id = task_spec.get("task_id", str(uuid.uuid4()))
        task = AgentTask(
            task_id=task_id,
            description=task_spec.get("description", ""),
            required_capabilities=set(task_spec.get("required_capabilities", [])),
            priority=task_spec.get("priority", 5),
            assigned_agent=task_spec.get("assigned_agent"),
        )
        with self._lock:
            self._tasks[task_id] = task
        return task
