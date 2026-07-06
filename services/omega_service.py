from __future__ import annotations

from omega.ecosystem_base import (
    PluginMarketplace,
    MultiAgentCoordinator,
    DistributedRuntimeRegistry,
    PolicyManager,
    PublicApiCatalog,
)
from omega.ecosystem import (
    AgentCoordinator,
    TaskPlanner,
    ConsensusEngine,
    DelegationRouter,
    NodeRegistry,
    DistributedRuntime,
    KnowledgeSynchronizer,
    CapabilitySynchronizer,
    PolicyEngine,
    PermissionHierarchy,
    RuleEngine,
    PolicyAuditLogger,
    PluginRepository,
    CapabilityRepository,
    DriverRepository,
    AgentRepository,
    OrganizationRegistry,
    ProjectRegistry,
    UserRegistry,
    TeamRegistry,
    RoleRegistry,
    ResourceManager,
    MemoryManager,
    LifecycleManager,
    DashboardHub,
)


class OmegaService:
    def __init__(self, epsilon_service=None, kernel=None):
        self._marketplace = PluginMarketplace()
        self._coordinator = MultiAgentCoordinator()
        self._runtime = DistributedRuntimeRegistry()
        self._policy = PolicyManager()
        self._catalog = PublicApiCatalog()

        self._agent_coordinator = AgentCoordinator()
        self._task_planner = TaskPlanner()
        self._consensus = ConsensusEngine()
        self._delegation = DelegationRouter()

        self._node_registry = NodeRegistry()
        self._distributed_runtime = DistributedRuntime()
        self._knowledge_sync = KnowledgeSynchronizer()
        self._capability_sync = CapabilitySynchronizer()

        self._policy_engine = PolicyEngine()
        self._permission_hierarchy = PermissionHierarchy()
        self._rule_engine = RuleEngine()
        self._policy_audit = PolicyAuditLogger()

        self._plugin_repo = PluginRepository()
        self._capability_repo = CapabilityRepository()
        self._driver_repo = DriverRepository()
        self._agent_repo = AgentRepository()

        self._org_registry = OrganizationRegistry()
        self._project_registry = ProjectRegistry()
        self._user_registry = UserRegistry()
        self._team_registry = TeamRegistry()
        self._role_registry = RoleRegistry()

        self._resource_manager = ResourceManager()
        self._memory_manager = MemoryManager()
        self._lifecycle_manager = LifecycleManager()

        self._dashboard = DashboardHub()
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

    def coordinate_agents(self, tasks: list[dict]) -> dict:
        return self._agent_coordinator.coordinate(tasks)

    def plan_tasks(self, objective: str, available_agents: list[str], capabilities: dict) -> dict:
        graph = self._task_planner.plan(objective, available_agents, capabilities)
        return {
            "objective": objective,
            "tasks": [t for t in graph.topological_sort()],
        }

    def consensus_propose(self, proposal: dict, participants: list[str]) -> dict:
        result = self._consensus.propose(proposal, participants)
        return result.to_dict()

    def delegate_task(self, from_agent: str, to_agent: str, task: dict) -> dict:
        result = self._delegation.delegate(from_agent, to_agent, task)
        return result.to_dict()

    def get_dashboard(self, section: str = "overview") -> dict:
        return self._dashboard.get_dashboard(section)
