from __future__ import annotations

from distributed.capability_executor import DistributedCapabilityExecutor
from cloud.workspace_sync import WorkspaceSync
from marketplace.capability_packaging import CapabilityPackager


_DISTRIBUTED_CAPABILITIES: dict[str, tuple[Any, set[str]]] = {
    "distributed.capability.execute": (
        DistributedCapabilityExecutor().execute_on_node,
        {"device.connect"},
    ),
    "distributed.capability.broadcast": (
        DistributedCapabilityExecutor().broadcast_capability,
        {"device.connect"},
    ),
    "cloud.workspace.sync": (
        WorkspaceSync().sync_workspace,
        {"team.workspace.write"},
    ),
    "cloud.workspace.resolve_conflicts": (
        WorkspaceSync().conflict_resolve,
        {"team.workspace.write"},
    ),
    "marketplace.capability.package": (
        CapabilityPackager().package_capability,
        {"plugin.install"},
    ),
    "marketplace.capability.verify": (
        CapabilityPackager().verify_package,
        {"plugin.install"},
    ),
    "marketplace.capability.install": (
        CapabilityPackager().install_package,
        {"plugin.install"},
    ),
}


def register_distributed_capabilities(capability_api) -> None:
    for name, (executor, permissions) in _DISTRIBUTED_CAPABILITIES.items():
        if capability_api.exists(name):
            continue
        capability_api.register(
            name=name,
            target="distributed",
            description=f"Distributed capability: {name}",
            permissions=set(permissions),
            executor=executor,
        )
