from __future__ import annotations

from dataclasses import dataclass, field

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TaskNode:
    task_id: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    assigned_agent: str | None = None


class TaskGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, TaskNode] = {}

    def add_task(self, task_id: str, description: str, dependencies: list[str], estimated_duration: float = 0.0) -> TaskNode:
        node = TaskNode(task_id=task_id, description=description, dependencies=dependencies, estimated_duration=estimated_duration)
        self._nodes[task_id] = node
        return node

    def topological_sort(self) -> list[str]:
        visited = set()
        result = []
        def visit(nid: str):
            if nid in visited:
                return
            visited.add(nid)
            node = self._nodes.get(nid)
            if node:
                for dep in node.dependencies:
                    visit(dep)
            result.append(nid)
        for nid in self._nodes:
            visit(nid)
        return result

    def get_critical_path(self) -> list[str]:
        return self.topological_sort()

    def validate(self) -> list[str]:
        errors = []
        for nid, node in self._nodes.items():
            for dep in node.dependencies:
                if dep not in self._nodes:
                    errors.append(f"Task {nid} depends on missing task {dep}")
        return errors

    def get_ready_tasks(self) -> list[TaskNode]:
        completed = set()
        ready = []
        for node in self._nodes.values():
            if all(dep in completed for dep in node.dependencies):
                ready.append(node)
                completed.add(node.task_id)
        return ready


class TaskPlanner:
    def plan(self, objective: str, available_agents: list[str], capabilities: dict) -> TaskGraph:
        graph = TaskGraph()
        graph.add_task("root", objective, [], 0.0)
        return graph

    def optimize(self, graph: TaskGraph) -> TaskGraph:
        return graph
