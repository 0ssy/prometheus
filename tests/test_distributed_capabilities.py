from __future__ import annotations

from distributed.capability_executor import DistributedCapabilityExecutor
from cloud.workspace_sync import WorkspaceSync
from marketplace.capability_packaging import CapabilityPackager


def test_execute_on_node_returns_stub():
    executor = DistributedCapabilityExecutor()
    result = executor.execute_on_node(
        node_id="node-1",
        capability_name="distributed.capability.execute",
        payload={"key": "value"},
        granted_permissions={"device.connect"},
    )
    assert result == {
        "node_id": "node-1",
        "capability": "distributed.capability.execute",
        "result": None,
        "status": "stub",
    }


def test_broadcast_capability_returns_empty_list():
    executor = DistributedCapabilityExecutor()
    result = executor.broadcast_capability(
        capability_name="distributed.capability.broadcast",
        payload={"key": "value"},
        granted_permissions={"device.connect"},
    )
    assert result == []


def test_workspace_sync_returns_stub():
    sync = WorkspaceSync()
    result = sync.sync_workspace(workspace_id="ws-1", team_id="team-1")
    assert result == {
        "workspace_id": "ws-1",
        "team_id": "team-1",
        "status": "stub",
    }


def test_conflict_resolve_returns_stub():
    sync = WorkspaceSync()
    conflicts = [{"id": 1}, {"id": 2}]
    result = sync.conflict_resolve(workspace_id="ws-1", conflicts=conflicts)
    assert result == {
        "workspace_id": "ws-1",
        "resolved": 2,
        "status": "stub",
    }


def test_capability_packager_package_returns_stub():
    packager = CapabilityPackager()
    result = packager.package_capability(
        capability_name="my-cap",
        version="1.0.0",
        executor_path="/path/to/executor.py",
    )
    assert result == {
        "name": "my-cap",
        "version": "1.0.0",
        "format": "prometheus-cap",
        "status": "stub",
    }


def test_capability_packager_verify_returns_stub():
    packager = CapabilityPackager()
    result = packager.verify_package(package_data=b"fake-package")
    assert result == {"valid": False, "status": "stub"}


def test_capability_packager_install_returns_stub():
    packager = CapabilityPackager()
    result = packager.install_package(package_data=b"fake-package")
    assert result == {"installed": False, "status": "stub"}
