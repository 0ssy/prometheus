from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class VirtualWorkspace:
    workspace_id: str
    virtual_devices: list[dict[str, Any]]
    virtual_networks: list[dict[str, Any]]
    virtual_sensors: list[dict[str, Any]]
    virtual_filesystems: list[dict[str, Any]]
    virtual_users: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DigitalEngineeringLab:
    def __init__(self):
        self._workspaces: dict[str, VirtualWorkspace] = {}

    def create_workspace(self, workspace_id: str, device_count: int = 1) -> dict[str, Any]:
        if device_count < 1:
            raise ValueError("device_count must be >= 1")
        devices = [
            {
                "id": f"{workspace_id}.dev{i}",
                "state": "online",
                "power": {"battery_health": 1.0, "temperature_c": 33.0},
                "performance": {"latency_ms": 5.0, "throughput": 1.0},
            }
            for i in range(device_count)
        ]
        workspace = VirtualWorkspace(
            workspace_id=workspace_id,
            virtual_devices=devices,
            virtual_networks=[{"id": f"{workspace_id}.net0", "status": "healthy"}],
            virtual_sensors=[{"id": f"{workspace_id}.sensor0", "status": "healthy"}],
            virtual_filesystems=[{"id": f"{workspace_id}.fs0", "status": "healthy"}],
            virtual_users=[{"id": f"{workspace_id}.user0", "role": "operator"}],
        )
        self._workspaces[workspace_id] = workspace
        return workspace.to_dict()

    def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._workspaces.get(workspace_id)
        if workspace is None:
            raise RuntimeError(f"No such workspace: {workspace_id}")
        return workspace.to_dict()

    def inject_failure(self, workspace_id: str, failure_type: str) -> dict[str, Any]:
        workspace = self._workspaces.get(workspace_id)
        if workspace is None:
            raise RuntimeError(f"No such workspace: {workspace_id}")
        if failure_type == "network":
            workspace.virtual_networks[0]["status"] = "degraded"
        elif failure_type == "storage":
            workspace.virtual_filesystems[0]["status"] = "corrupt"
        elif failure_type == "power":
            for device in workspace.virtual_devices:
                device["power"]["battery_health"] = max(
                    0.1, device["power"]["battery_health"] - 0.2
                )
        elif failure_type == "security":
            workspace.virtual_users[0]["role"] = "compromised"
        else:
            raise ValueError("failure_type must be one of: network, storage, power, security")
        return workspace.to_dict()
