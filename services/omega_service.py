from __future__ import annotations

from omega.ecosystem import (
    DistributedRuntimeRegistry,
    MultiAgentCoordinator,
    PluginMarketplace,
    PolicyManager,
    PublicApiCatalog,
)


class OmegaService:
    def __init__(self):
        self._marketplace = PluginMarketplace()
        self._coordinator = MultiAgentCoordinator()
        self._runtime = DistributedRuntimeRegistry()
        self._policy = PolicyManager()
        self._catalog = PublicApiCatalog()

    def publish_plugin(self, plugin: dict) -> dict:
        return self._marketplace.publish(plugin)

    def list_plugins(self) -> list[dict]:
        return self._marketplace.list_plugins()

    def plan_collaboration(self, tasks: list[str]) -> dict:
        return self._coordinator.plan(tasks)

    def register_node(self, node_id: str) -> dict:
        self._runtime.register_node(node_id)
        return {"nodes": self._runtime.list_nodes()}

    def list_nodes(self) -> dict:
        return {"nodes": self._runtime.list_nodes()}

    def grant_permission(self, actor: str, permission: str) -> dict:
        self._policy.grant(actor, permission)
        return {"actor": actor, "permission": permission, "granted": True}

    def check_permission(self, actor: str, permission: str) -> dict:
        return {
            "actor": actor,
            "permission": permission,
            "allowed": self._policy.check(actor, permission),
        }

    def public_apis(self) -> dict:
        return {"apis": self._catalog.list_apis()}
