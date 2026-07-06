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
    delta_service = DeltaService(
        knowledge_engine=components.knowledge_engine,
        device_api=components.device_api,
        session_factory=SessionLocal,
    )
    epsilon_service = EpsilonService(
        device_api=components.device_api,
        delta_service=delta_service,
        session_factory=SessionLocal,
    )
    omega_service = OmegaService(
        epsilon_service=epsilon_service,
        kernel=kernel,
    )

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

    logger.info("Startup complete - Prometheus Core (Delta Daedalus) runtime online")
    return container
