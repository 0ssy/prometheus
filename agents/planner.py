"""
Prometheus Multi-Agent Coordination — Planner
-------------------------------------------------
Builds a dependency graph of tasks from a high-level objective, performs
topological ordering and critical-path analysis, and validates that the
graph is a well-formed DAG.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TaskNode:
    task_id: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    estimated_duration: float = 1.0
    assigned_agent: str | None = None


class TaskGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, TaskNode] = {}
        self._lock = threading.RLock()

    def add_task(
        self,
        task_id: str,
        description: str,
        dependencies: list[str] | None = None,
        estimated_duration: float = 1.0,
    ) -> TaskNode:
        with self._lock:
            node = TaskNode(
                task_id=task_id,
                description=description,
                dependencies=list(dependencies or []),
                estimated_duration=estimated_duration,
            )
            self._nodes[task_id] = node
        logger.info(f"Added task node {task_id} (deps={node.dependencies})")
        return node

    def get_node(self, task_id: str) -> TaskNode | None:
        with self._lock:
            return self._nodes.get(task_id)

    def all_nodes(self) -> list[TaskNode]:
        with self._lock:
            return list(self._nodes.values())

    def topological_sort(self) -> list[str]:
        with self._lock:
            nodes = dict(self._nodes)
        order: list[str] = []
        visited: set[str] = set()
        temp: set[str] = set()

        def visit(nid: str) -> None:
            if nid in visited:
                return
            if nid in temp:
                raise ValueError(f"Cycle detected at task {nid}")
            if nid not in nodes:
                return
            temp.add(nid)
            for dep in nodes[nid].dependencies:
                visit(dep)
            temp.discard(nid)
            visited.add(nid)
            order.append(nid)

        for nid in nodes:
            visit(nid)
        return order

    def get_critical_path(self) -> list[str]:
        with self._lock:
            nodes = dict(self._nodes)
        order = self.topological_sort()
        longest_end: dict[str, float] = {}
        predecessor: dict[str, str | None] = {}

        for nid in order:
            node = nodes[nid]
            start = 0.0
            pred: str | None = None
            for dep in node.dependencies:
                if dep in longest_end and longest_end[dep] > start:
                    start = longest_end[dep]
                    pred = dep
            longest_end[nid] = start + node.estimated_duration
            predecessor[nid] = pred

        if not longest_end:
            return []
        end_node = max(longest_end, key=lambda k: longest_end[k])
        path: list[str] = []
        cur: str | None = end_node
        while cur is not None:
            path.append(cur)
            cur = predecessor.get(cur)
        path.reverse()
        return path

    def validate(self) -> list[str]:
        errors: list[str] = []
        with self._lock:
            nodes = dict(self._nodes)
        for nid, node in nodes.items():
            for dep in node.dependencies:
                if dep not in nodes:
                    errors.append(f"Task '{nid}' depends on unknown task '{dep}'")
        try:
            self.topological_sort()
        except ValueError as exc:
            errors.append(str(exc))
        return errors

    def get_ready_tasks(self) -> list[TaskNode]:
        with self._lock:
            nodes = dict(self._nodes)
        ready = []
        for nid, node in nodes.items():
            if node.assigned_agent is not None:
                continue
            if all(dep in nodes for dep in node.dependencies):
                ready.append(node)
        return sorted(ready, key=lambda n: n.estimated_duration)


class TaskPlanner:
    def __init__(self) -> None:
        self._lock = threading.RLock()

    def plan(
        self,
        objective: str,
        available_agents: list[str],
        capabilities: dict[str, Any],
    ) -> TaskGraph:
        logger.info(f"Planning objective: {objective}")
        graph = TaskGraph()
        graph.add_task("analyze", f"Analyze objective: {objective}", [], estimated_duration=1.0)
        graph.add_task(
            "decompose",
            "Decompose into subtasks",
            ["analyze"],
            estimated_duration=1.0,
        )
        graph.add_task(
            "execute",
            "Execute subtasks across agents",
            ["decompose"],
            estimated_duration=2.0,
        )
        graph.add_task(
            "verify",
            "Verify objective completion",
            ["execute"],
            estimated_duration=1.0,
        )
        agent_cycle = list(available_agents) or ["planner"]
        for i, node in enumerate(graph.all_nodes()):
            node.assigned_agent = agent_cycle[i % len(agent_cycle)]
        logger.info(f"Planned graph with {len(graph.all_nodes())} tasks")
        return graph

    def optimize(self, graph: TaskGraph) -> TaskGraph:
        logger.info("Optimizing task graph (no-op passthrough for Phase Omega)")
        return graph
