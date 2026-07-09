"""
Prometheus Core Bootstrap
-----------------------------------------
The single entry point that boots the platform. Backed by a
ServiceContainer that wires every subsystem explicitly.

boot() returns the populated container so callers can hand a fully
orchestrated platform to a test harness, CLI, or API layer without
repeating wiring logic.

Sequence:
  Load Config -> Init Database -> Build Implementations -> Bind Events ->
  Load Plugins -> Load Agents -> Start Scheduler
"""

from collections.abc import Callable

from core.config import config
from core.container import ServiceContainer
from core.database import init_db
from core.event_bus import InMemoryEventBus
from core.logger import get_logger
from core.observability import ObservabilityStore
from implementations.platform_components import build_platform_components
from kernel.runtime import PrometheusCoreKernel
from services.delta_service import DeltaService
from services.epsilon_service import EpsilonService
from services.event_handlers import PlatformEventHandlers
from services.omega_service import OmegaService
from services.platform_service import PlatformService

logger = get_logger(__name__)


def _load_database(container: ServiceContainer) -> None:
    init_db()
    from core.database import engine

    container.register("db_engine", engine)


def _register_services(container: ServiceContainer) -> None:
    from core.database import SessionLocal

    event_bus = InMemoryEventBus()
    observability = ObservabilityStore()
    components = build_platform_components(event_bus=event_bus)
    platform_service = PlatformService(
        plugin_api=components.plugin_api,
        agent_api=components.agent_api,
        capability_api=components.capability_api,
        device_api=components.device_api,
        memory_api=components.memory_api,
        reasoning_api=components.reasoning_api,
        event_bus=event_bus,
        knowledge_engine=components.knowledge_engine,
        session_factory=SessionLocal,
        observability=observability,
    )
    event_handlers = PlatformEventHandlers(
        event_bus=event_bus,
        session_factory=SessionLocal,
        memory_api=components.memory_api,
        reasoning_api=components.reasoning_api,
        observability=observability,
    )
    event_handlers.bind()
    kernel = PrometheusCoreKernel(
        capability_api=components.capability_api,
        scheduler=components.scheduler,
        version=config.version,
    )
    kernel.start()
    kernel.grant_permission("system", "device.recover")
    kernel.grant_permission("system", "device.diagnose")
    kernel.grant_permission("system", "hardware.session.create")
    kernel.grant_permission("system", "firmware.read")
    delta_service = DeltaService(
        knowledge_engine=components.knowledge_engine,
        device_api=components.device_api,
        session_factory=SessionLocal,
    )
    epsilon_service = EpsilonService(
        device_api=components.device_api,
        delta_service=delta_service,
        session_factory=SessionLocal,
        event_bus=event_bus,
        knowledge_engine=components.knowledge_engine,
    )
    omega_service = OmegaService(
        epsilon_service=epsilon_service,
        kernel=kernel,
    )

    from simulation.engine import SimulationEngine
    simulation_engine = SimulationEngine()

    container.register("event_bus", event_bus)
    container.register("observability", observability)
    container.register("scheduler", components.scheduler)
    container.register("session_factory", SessionLocal)
    container.register("memory_api", components.memory_api)
    container.register("reasoning_api", components.reasoning_api)
    container.register("knowledge_engine", components.knowledge_engine)
    container.register("plugin_api", components.plugin_api)
    container.register("agent_api", components.agent_api)
    container.register("capability_api", components.capability_api)
    container.register("device_api", components.device_api)
    container.register("platform_service", platform_service)
    container.register("delta_service", delta_service)
    container.register("epsilon_service", epsilon_service)
    container.register("omega_service", omega_service)
    container.register("event_handlers", event_handlers)
    container.register("kernel", kernel)
    container.register("simulation_engine", simulation_engine)
    container.register("hardware_hal", epsilon_service._hal)
    container.register("hardware_session_manager", epsilon_service._session_manager)
    container.register("hardware_diagnostics", epsilon_service._diagnostics)
    container.register("hardware_recovery", epsilon_service._recovery)
    container.register("hardware_firmware", epsilon_service._firmware)
    container.register("security_authorizer", epsilon_service._authorizer)
    container.register("security_audit", epsilon_service._audit)
    container.register("security_integrity", epsilon_service._integrity)
    container.register("omega_agent_coordinator", omega_service._agent_coordinator)
    container.register("omega_task_planner", omega_service._task_planner)
    container.register("omega_consensus", omega_service._consensus)
    container.register("omega_delegation", omega_service._delegation)
    container.register("omega_node_registry", omega_service._node_registry)
    container.register("omega_distributed_runtime", omega_service._distributed_runtime)
    container.register("omega_knowledge_sync", omega_service._knowledge_sync)
    container.register("omega_capability_sync", omega_service._capability_sync)
    container.register("omega_policy_engine", omega_service._policy_engine)
    container.register("omega_permission_hierarchy", omega_service._permission_hierarchy)
    container.register("omega_rule_engine", omega_service._rule_engine)
    container.register("omega_policy_audit", omega_service._policy_audit)
    container.register("omega_plugin_repo", omega_service._plugin_repo)
    container.register("omega_capability_repo", omega_service._capability_repo)
    container.register("omega_driver_repo", omega_service._driver_repo)
    container.register("omega_agent_repo", omega_service._agent_repo)
    container.register("omega_org_registry", omega_service._org_registry)
    container.register("omega_project_registry", omega_service._project_registry)
    container.register("omega_user_registry", omega_service._user_registry)
    container.register("omega_team_registry", omega_service._team_registry)
    container.register("omega_role_registry", omega_service._role_registry)
    container.register("omega_resource_manager", omega_service._resource_manager)
    container.register("omega_memory_manager", omega_service._memory_manager)
    container.register("omega_lifecycle_manager", omega_service._lifecycle_manager)
    container.register("omega_dashboard", omega_service._dashboard)


def _load_plugins(container: ServiceContainer) -> None:
    from plugins.installed.echo_plugin import EchoPlugin

    plugin_api = container.get("plugin_api")
    plugin_api.register(EchoPlugin())


def _load_agents(container: ServiceContainer) -> None:
    from agents.echo_agent import EchoAgent
    from autonomous.engineering_agent import EngineeringAgent

    agent_api = container.get("agent_api")
    agent_api.register(EchoAgent())
    agent_api.register(EngineeringAgent())


def _start_scheduler(
    container: ServiceContainer, heartbeat_job: Callable[[], None]
) -> None:
    scheduler = container.get("scheduler")
    scheduler.schedule("heartbeat", heartbeat_job, interval_seconds=30)
    scheduler.start()


def boot(heartbeat_job: Callable[[], None]) -> ServiceContainer:
    container = ServiceContainer()
    container.register("config", config)

    _load_database(container)
    _register_services(container)
    _load_plugins(container)
    _load_agents(container)
    _start_scheduler(container, heartbeat_job)

    logger.info("Startup complete - Prometheus Core (Omega Olympus) runtime online")
    return container
