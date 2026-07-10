from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agents.planner import TaskGraph, TaskNode
from core.logger import get_logger

logger = get_logger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
WORKFLOWS_FILE = CONFIG_DIR / "workflows.json"


@dataclass
class WorkflowStep:
    step_id: str
    description: str
    action: str
    status: str = "pending"
    result: dict[str, Any] = field(default_factory=dict)
    started_at: float | None = None
    finished_at: float | None = None
    failed_at: float | None = None


@dataclass
class Workflow:
    id: str
    name: str
    steps: list[WorkflowStep]
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    last_run: float | None = None
    results: list[dict[str, Any]] = field(default_factory=list)


class WorkflowRuntime:
    def __init__(self, workflows_path: Path | None = None) -> None:
        self._path = workflows_path or WORKFLOWS_FILE
        self._workflows: dict[str, Workflow] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            self._seed_default()
            return
        try:
            data = json.loads(self._path.read_text())
            for wf in data.get("workflows", []):
                steps = [
                    WorkflowStep(
                        step_id=s["step_id"],
                        description=s["description"],
                        action=s["action"],
                        status=s.get("status", "pending"),
                        result=s.get("result", {}),
                        started_at=s.get("started_at"),
                        finished_at=s.get("finished_at"),
                        failed_at=s.get("failed_at"),
                    )
                    for s in wf.get("steps", [])
                ]
                workflow = Workflow(
                    id=wf["id"],
                    name=wf["name"],
                    steps=steps,
                    status=wf.get("status", "pending"),
                    created_at=wf.get("created_at", time.time()),
                    last_run=wf.get("last_run"),
                    results=wf.get("results", []),
                )
                self._workflows[workflow.id] = workflow
        except Exception:
            logger.exception("Failed to load workflows")

    def _persist(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "workflows": [
                    {
                        "id": wf.id,
                        "name": wf.name,
                        "status": wf.status,
                        "created_at": wf.created_at,
                        "last_run": wf.last_run,
                        "results": wf.results,
                        "steps": [
                            {
                                "step_id": s.step_id,
                                "description": s.description,
                                "action": s.action,
                                "status": s.status,
                                "result": s.result,
                                "started_at": s.started_at,
                                "finished_at": s.finished_at,
                                "failed_at": s.failed_at,
                            }
                            for s in wf.steps
                        ],
                    }
                    for wf in self._workflows.values()
                ]
            }
            self._path.write_text(json.dumps(payload, indent=2))
        except Exception:
            logger.exception("Failed to persist workflows")

    def _seed_default(self) -> None:
        steps = [
            WorkflowStep(step_id="s1", description="Connect Device", action="capability:device.connect"),
            WorkflowStep(step_id="s2", description="Identify", action="capability:device.status"),
            WorkflowStep(step_id="s3", description="Create Digital Twin", action="agent:twin_builder"),
            WorkflowStep(step_id="s4", description="Run Diagnostics", action="capability:device.diagnose"),
            WorkflowStep(step_id="s5", description="Store Knowledge", action="memory:remember"),
            WorkflowStep(step_id="s6", description="Generate Report", action="capability:device.read"),
            WorkflowStep(step_id="s7", description="Notify User", action="notify"),
        ]
        wf = Workflow(id=str(uuid.uuid4()), name="Device Lifecycle", steps=steps)
        self._workflows[wf.id] = wf
        self._persist()

    def list_workflows(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._to_dict(wf) for wf in self._workflows.values()]

    def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        with self._lock:
            wf = self._workflows.get(workflow_id)
            return self._to_dict(wf) if wf else None

    def create_workflow(self, name: str, steps: list[dict[str, str]]) -> dict[str, Any]:
        with self._lock:
            workflow_steps = []
            for idx, s in enumerate(steps):
                workflow_steps.append(
                    WorkflowStep(
                        step_id=f"s{idx + 1}",
                        description=s.get("description", s.get("action", "")),
                        action=s.get("action", ""),
                    )
                )
            wf = Workflow(id=str(uuid.uuid4()), name=name, steps=workflow_steps)
            self._workflows[wf.id] = wf
            self._persist()
            return self._to_dict(wf)

    def run(self, workflow_id: str) -> dict[str, Any] | None:
        with self._lock:
            wf = self._workflows.get(workflow_id)
            if wf is None:
                return None
            wf.status = "running"
            wf.last_run = time.time()
            wf.results = []
            graph = TaskGraph()
            step_map: dict[str, WorkflowStep] = {}
            for step in wf.steps:
                step_map[step.step_id] = step
                graph.add_task(
                    task_id=step.step_id,
                    description=step.description,
                    dependencies=[],
                )
            for step in wf.steps:
                if step.action.startswith("after:"):
                    dep = step.action.split(":", 1)[1]
                    node = graph.get_node(step.step_id)
                    if node:
                        node.dependencies.append(dep)

        order = graph.topological_sort()
        for step_id in order:
            step = step_map[step_id]
            step.status = "running"
            step.started_at = time.time()
            step.finished_at = None
            step.failed_at = None
            step.result = {}
            self._persist()
            try:
                step.result = {"status": "simulated", "action": step.action}
                step.status = "done"
                step.finished_at = time.time()
                wf.results.append({"step_id": step.step_id, "status": "done", "result": step.result})
            except Exception as exc:
                step.status = "failed"
                step.failed_at = time.time()
                wf.results.append({"step_id": step.step_id, "status": "failed", "error": str(exc)})
                wf.status = "failed"
                self._persist()
                return self._to_dict(wf)
        wf.status = "completed"
        self._persist()
        return self._to_dict(wf)

    def _to_dict(self, wf: Workflow | None) -> dict[str, Any]:
        if wf is None:
            return {}
        return {
            "id": wf.id,
            "name": wf.name,
            "status": wf.status,
            "created_at": wf.created_at,
            "last_run": wf.last_run,
            "results": wf.results,
            "steps": [
                {
                    "step_id": s.step_id,
                    "description": s.description,
                    "action": s.action,
                    "status": s.status,
                    "result": s.result,
                    "started_at": s.started_at,
                    "finished_at": s.finished_at,
                    "failed_at": s.failed_at,
                }
                for s in wf.steps
            ],
        }
