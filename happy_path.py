"""
Happy Path — Complete Prometheus Platform Demo
----------------------------------------------
Runs every subsystem end-to-end: bootstrap, plugin execution, agent
dispatch, device lifecycle, memory persistence, knowledge-graph
queries, and digital twin assembly.
"""

from core.bootstrap import boot
from core.container import ServiceContainer
from core.config import config
from core.database import SessionLocal
from core.logger import get_logger
from services.platform_service import PlatformService

logger = get_logger(__name__)


def _heartbeat_job():
    pass


def run_happy_path() -> dict:
    logger.info("=== HAPPY PATH START ===")
    container = boot(_heartbeat_job)

    try:
        with SessionLocal() as db:
            _run_plugin(container, db)
            _run_agent(container, db)
            _create_device(container, db)
            _store_memory(container, db)
            _query_knowledge_graph(container, db)
            _build_twin(container, db)
            report = _generate_report(container, db)
    finally:
        container.get("scheduler").stop()

    logger.info("=== HAPPY PATH COMPLETE ===")
    return report


def _run_plugin(container: ServiceContainer, db) -> None:
    platform = container.resolve("platform_service", PlatformService)
    result = platform.run_plugin(db, plugin_name="echo", payload={"message": "hello from happy path"})
    logger.info(f"[plugin] echo ran -> {result}")


def _run_agent(container: ServiceContainer, db) -> None:
    platform = container.resolve("platform_service", PlatformService)
    result = platform.dispatch_agent(
        db, "echo_agent", {"device_id": "happy_device", "status": "seen"}
    )
    logger.info(f"[agent] echo_agent dispatched -> {result}")


def _create_device(container: ServiceContainer, db) -> None:
    platform = container.resolve("platform_service", PlatformService)
    result = platform.register_simulated_device(
        device_id="happy_device", ownership_declared=True
    )
    logger.info(f"[device] registered happy_device (transport={result['transport']})")


def _store_memory(container: ServiceContainer, db) -> None:
    platform = container.resolve("platform_service", PlatformService)
    entry = platform.store_memory(
        db, "Happy path executed successfully", tag="happy_path", source="demo"
    )
    logger.info(f"[memory] stored entry {entry.id}")


def _query_knowledge_graph(container: ServiceContainer, db) -> None:
    platform = container.resolve("platform_service", PlatformService)
    facts = platform.get_facts(db, subject="happy_device")
    logger.info(f"[reasoning] found {len(facts)} fact(s) for happy_device")
    for f in facts:
        logger.info(f"  -> {f.predicate}: {f.object}")


def _build_twin(container: ServiceContainer, db) -> None:
    from digital_twin.twin import build_twin

    twin = build_twin(db, "happy_device", device_api=container.get("device_api"))
    logger.info(
        f"[twin] built twin for happy_device: state={twin.state}, health={twin.health}"
    )


def _generate_report(container: ServiceContainer, db) -> dict:
    session = db
    from sqlalchemy import func
    from memory.models import MemoryEntry
    from reasoning.models import KnowledgeFact

    memory_count = session.query(func.count(MemoryEntry.id)).scalar()
    fact_count = session.query(func.count(KnowledgeFact.id)).scalar()

    report = {
        "platform": f"{config.app_name} v{config.version}",
        "plugins_loaded": container.get("plugin_api").list_plugins(),
        "agents_loaded": container.get("agent_api").list_agents(),
        "devices_registered": len(container.get("device_api").list()),
        "services_registered": container.list_services(),
        "memory_entries": int(memory_count or 0),
        "knowledge_facts": int(fact_count or 0),
        "status": "ok",
    }

    logger.info(f"[report] {report}")
    return report


if __name__ == "__main__":
    run_happy_path()
