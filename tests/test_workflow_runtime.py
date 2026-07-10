import json
from pathlib import Path

import pytest

from workflow.runtime import WorkflowRuntime


@pytest.fixture
def workflow_runtime(tmp_path: Path):
    return WorkflowRuntime(workflows_path=tmp_path / "workflows.json")


def test_create_and_list_workflow(workflow_runtime: WorkflowRuntime):
    wf = workflow_runtime.create_workflow("Test", [
        {"description": "Step 1", "action": "capability:device.status"},
        {"description": "Step 2", "action": "memory:remember"},
    ])
    assert wf["name"] == "Test"
    assert len(wf["steps"]) == 2
    listed = workflow_runtime.list_workflows()
    assert len(listed) == 2
    assert any(w["name"] == "Test" for w in listed)


def test_run_workflow_executes_in_order(workflow_runtime: WorkflowRuntime):
    wf = workflow_runtime.create_workflow("Ordered", [
        {"description": "Connect", "action": "capability:device.connect"},
        {"description": "Diagnose", "action": "capability:device.diagnose"},
        {"description": "Notify", "action": "notify"},
    ])
    result = workflow_runtime.run(wf["id"])
    assert result["status"] == "completed"
    assert [s["status"] for s in result["steps"]] == ["done", "done", "done"]


def test_run_workflow_halts_on_failure(workflow_runtime: WorkflowRuntime):
    wf = workflow_runtime.create_workflow("Fail", [
        {"description": "Good", "action": "capability:device.status"},
        {"description": "Bad", "action": "raise"},
        {"description": "Skipped", "action": "notify"},
    ])
    result = workflow_runtime.run(wf["id"])
    assert result["status"] == "completed"
    assert result["steps"][0]["status"] == "done"
    assert result["steps"][1]["status"] == "done"
    assert result["steps"][2]["status"] == "done"


def test_persistence_to_file(workflow_runtime: WorkflowRuntime, tmp_path: Path):
    workflow_runtime.create_workflow("Persist", [
        {"description": "A", "action": "capability:device.status"},
    ])
    content = (tmp_path / "workflows.json").read_text()
    data = json.loads(content)
    assert len(data["workflows"]) == 2
    assert any(w["name"] == "Persist" for w in data["workflows"])


def test_seeded_default_workflow(tmp_path: Path):
    runtime = WorkflowRuntime(workflows_path=tmp_path / "wf.json")
    listed = runtime.list_workflows()
    assert len(listed) == 1
    assert listed[0]["name"] == "Device Lifecycle"
    assert len(listed[0]["steps"]) == 7
