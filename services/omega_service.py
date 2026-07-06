from __future__ import annotations

from omega.ecosystem import (
    DistributedRuntimeRegistry,
    MultiAgentCoordinator,
    PluginMarketplace,
    PolicyManager,
    PublicApiCatalog,
)


class OmegaService:
    def __init__(self, epsilon_service=None, kernel=None):
        self._marketplace = PluginMarketplace()
        self._coordinator = MultiAgentCoordinator()
        self._runtime = DistributedRuntimeRegistry()
        self._policy = PolicyManager()
        self._catalog = PublicApiCatalog()
        self._epsilon_service = epsilon_service
        self._kernel = kernel

    def publish_plugin(self, plugin: dict) -> dict:
        return self._marketplace.publish(plugin)

    def list_plugins(self) -> list[dict]:
        return self._marketplace.list_plugins()

    def plan_collaboration(self, tasks: list[str]) -> dict:
        if self._epsilon_service is not None:
            try:
                self._epsilon_service.list_interfaces()
                tasks = [f"[hal] {t}" for t in tasks]
            except Exception:
                pass
        return self._coordinator.plan(tasks)

    def register_node(self, node_id: str) -> dict:
        self._runtime.register_node(node_id)
        return {"nodes": self._runtime.list_nodes()}

    def list_nodes(self) -> dict:
        return {"nodes": self._runtime.list_nodes()}

    def grant_permission(self, actor: str, permission: str) -> dict:
        if self._kernel is not None:
            self._kernel.grant_permission(actor, permission)
            return {"actor": actor, "permission": permission, "granted": True}
        self._policy.grant(actor, permission)
        return {"actor": actor, "permission": permission, "granted": True}

    def check_permission(self, actor: str, permission: str) -> dict:
        if self._kernel is not None:
            return {
                "actor": actor,
                "permission": permission,
                "allowed": self._kernel._permissions.check(actor, {permission}),
            }
        return {
            "actor": actor,
            "permission": permission,
            "allowed": self._policy.check(actor, permission),
        }

    def public_apis(self) -> dict:
        return {"apis": self._catalog.list_apis()}
