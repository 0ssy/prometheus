"""
Prometheus Core Bootstrap
-----------------------------------------
The single entry point that boots the platform, per the external
architecture review: "You have the modules. You don't yet have the
orchestration layer." This was previously buried inside FastAPI's
@app.on_event("startup") hook in backend/main.py, mixed in with route
definitions — readable to whoever wrote it, not to a new contributor
skimming the codebase for "how does this thing actually start."

boot() is intentionally a plain function, not tied to FastAPI at all —
that's what makes this "the orchestration layer" rather than just a
renamed startup hook. backend/main.py calls it; a future CLI entry
point or test harness could call it too, without needing a web server
running at all.

Sequence matches the review's suggested shape:
  Load Config -> Load Plugins -> Load Devices -> Load Agents ->
  Load Knowledge Graph -> Start Scheduler -> (Expose API happens
  separately, in backend/main.py, since that's a web-framework concern
  not a platform-boot concern)

"Load Devices" and "Load Knowledge Graph" are no-ops today — the
device registry starts empty by design (RFC 0001: devices reconnect
after a restart, no persistence yet) and the knowledge graph is just
the database connection, already handled by init_db(). They're listed
explicitly below anyway, so the boot sequence documents the platform's
actual shape even where a step currently does nothing.
"""
from collections.abc import Callable

from core.config import config
from core.database import init_db
from core.logger import get_logger
from core.scheduler import scheduler

from plugins.manager import plugin_manager
from plugins.installed.echo_plugin import EchoPlugin

from agents.manager import agent_manager
from agents.echo_agent import EchoAgent
from autonomous.engineering_agent import EngineeringAgent

logger = get_logger(__name__)


def _load_config() -> None:
    logger.info(f"Starting {config.app_name} v{config.version}")


def _load_database() -> None:
    init_db()


def _load_plugins() -> None:
    plugin_manager.register(EchoPlugin())


def _load_devices() -> None:
    # No-op for v0.1 — devices/registry.py starts empty on every boot,
    # by design (RFC 0001). Named explicitly so the sequence stays
    # honest about what actually happens at startup.
    pass


def _load_agents() -> None:
    agent_manager.register(EchoAgent())
    agent_manager.register(EngineeringAgent())


def _load_knowledge_graph() -> None:
    # No-op beyond init_db() above — the knowledge graph IS the
    # database in v0.1 (reasoning/models.py's KnowledgeFact table).
    # Listed as its own step to document the platform's conceptual
    # shape, not because there's separate work to do here yet.
    pass


def _start_scheduler(heartbeat_job: Callable[[], None]) -> None:
    scheduler.schedule("heartbeat", heartbeat_job, interval_seconds=30)
    scheduler.start()


def boot(heartbeat_job: Callable[[], None]) -> None:
    """
    The one function that boots Prometheus. heartbeat_job is passed in
    rather than imported, so this module doesn't depend on backend/
    at all — bootstrap.py could be reused by a future CLI or test
    harness that has no web server involved.
    """
    _load_config()
    _load_database()
    _load_plugins()
    _load_devices()
    _load_agents()
    _load_knowledge_graph()
    _start_scheduler(heartbeat_job)
    logger.info("Startup complete — Phase Alpha milestone checklist online")
