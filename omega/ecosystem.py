from __future__ import annotations


class PluginMarketplace:
    def __init__(self):
        self._plugins: list[dict] = []

    def publish(self, plugin: dict) -> dict:
        self._plugins.append(plugin)
        return plugin

    def list_plugins(self) -> list[dict]:
        return list(self._plugins)


class MultiAgentCoordinator:
    def plan(self, tasks: list[str]) -> dict:
        agents = ["recovery_agent", "hardware_agent", "knowledge_agent", "security_agent"]
        assignments = []
        for i, task in enumerate(tasks):
            assignments.append({"task": task, "agent": agents[i % len(agents)]})
        return {"assignments": assignments}


class DistributedRuntimeRegistry:
    def __init__(self):
        self._nodes: set[str] = set()

    def register_node(self, node_id: str) -> None:
        self._nodes.add(node_id)

    def list_nodes(self) -> list[str]:
        return sorted(self._nodes)


class PolicyManager:
    def __init__(self):
        self._permissions: dict[str, set[str]] = {}

    def grant(self, actor: str, permission: str) -> None:
        self._permissions.setdefault(actor, set()).add(permission)

    def check(self, actor: str, permission: str) -> bool:
        return permission in self._permissions.get(actor, set())


class PublicApiCatalog:
    def list_apis(self) -> list[str]:
        return [
            "CLI",
            "Web UI",
            "REST API",
            "Python SDK",
            "Automation API",
        ]
