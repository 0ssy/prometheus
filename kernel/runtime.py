from __future__ import annotations

from typing import Any

from contracts.capability import CapabilityApi
from contracts.scheduler import SchedulerApi
from kernel.lifecycle import LifecycleManager
from kernel.permissions import PermissionManager
from kernel.registry import KernelRegistry


class PrometheusCoreKernel:
    def __init__(
        self, capability_api: CapabilityApi, scheduler: SchedulerApi, version: str
    ):
        self._capability_api = capability_api
        self._scheduler = scheduler
        self._version = version
        self._lifecycle = LifecycleManager()
        self._permissions = PermissionManager()
        self._registry = KernelRegistry()
        self._registry.register("capability_api", capability_api)
        self._registry.register("scheduler", scheduler)

    def start(self) -> None:
        self._lifecycle.mark_started()

    def version(self) -> str:
        return self._version

    def status(self) -> dict[str, Any]:
        return {
            "kernel": "Prometheus Core Kernel",
            "version": self._version,
            "lifecycle": self._lifecycle.status(),
            "registered_services": self._registry.list_entries(),
            "scheduled_jobs": self._scheduler.list_jobs(),
            "capability_count": len(self._capability_api.discover()),
        }

    def health(self) -> dict[str, Any]:
        lifecycle = self._lifecycle.status()
        return {
            "status": "ok" if lifecycle["running"] else "stopped",
            "running": lifecycle["running"],
            "scheduler_jobs": len(self._scheduler.list_jobs()),
            "capabilities": len(self._capability_api.discover()),
        }

    def grant_permission(self, actor: str, permission: str) -> None:
        self._permissions.grant(actor, permission)

    def execute_capability_as(
        self, actor: str, capability_name: str, payload: dict[str, Any]
    ) -> Any:
        permissions = self._permissions.permissions_for(actor)
        return self._capability_api.execute(capability_name, payload, permissions)

    def shutdown(self) -> None:
        self._lifecycle.shutdown()
