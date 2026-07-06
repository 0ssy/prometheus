"""
Prometheus Core Bootstrap
-----------------------------------------
The single entry point that boots the platform. Backed by a
ServiceContainer that wires every subsystem explicitly.

boot() returns the populated container so callers can hand a fully
orchestrated platform to a test harness, CLI, or API layer without
repeating wiring logic.

Sequence:
  Load Config -> Init Database -> Register Services -> Load Plugins ->
  Load Agents -> Start Scheduler
"""

from collections.abc import Callable

from core.config import config
from core.event_bus import event_bus

logger = get_logger(__name__)


def _load_database(container: ServiceContainer) -> None:
    init_db()
    from core.database import engine

    container.register("db_engine", engine)


def _register_services(container: ServiceContainer) -> None:
    from core.database import SessionLocal
    from core.event_bus import event_bus
    from memory.store import memory_store
    from reasoning.graph import reasoning_store
    from plugins.manager import plugin_manager
    from agents.manager import agent_manager
    from devices.registry import device_registry

    container.register("event_bus", event_bus)
    container.register("session_factory", SessionLocal)
    container.register("memory_api", memory_store)
    container.register("reasoning_api", reasoning_store)
    container.register("plugin_api", plugin_manager)
    container.register("agent_api", agent_manager)
    container.register("device_api", device_registry)


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
    scheduler.schedule("heartbeat", heartbeat_job, interval_seconds=30)
    scheduler.start()
    container.register("scheduler", scheduler)


def boot(heartbeat_job: Callable[[], None]) -> ServiceContainer:
    container = ServiceContainer()
    container.register("config", config)

    _load_database(container)
    _register_services(container)
    _load_plugins(container)
    _load_agents(container)
    _start_scheduler(container, heartbeat_job)

    logger.info("Startup complete — Phase Alpha milestone checklist online")
    return container
