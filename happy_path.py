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

logger = get_logger(__name__)


def _heartbeat_job():
    pass


def run_happy_path() -> None:
    logger.info("=== HAPPY PATH START ===")
    container = boot(_heartbeat_job)

    with SessionLocal() as db:
        _run_plugin(container, db)
        _run_agent(container, db)
        _create_device(container, db)
        _store_memory(container, db)
        _query_knowledge_graph(container, db)
        _build_twin(container, db)
        _generate_report(container, db)

    logger.info("=== HAPPY PATH COMPLETE ===")


def _run_plugin(container: ServiceContainer, db) -> None:
    plugin_api = container.get("plugin_api")
    ctx = {
        "db": db,
        "logger": get_logger("happy_path.plugin"),
        "message": "hello from happy path",
    }
    result = plugin_api.run("echo", ctx)
    logger.info(f"[plugin] echo ran -> {result}")


def _run_agent(container: ServiceContainer, db) -> None:
    agent_api = container.get("agent_api")
    ctx = {"db": db, "logger": get_logger("happy_path.agent")}
    result = agent_api.dispatch(
        "echo_agent", {"device_id": "happy_device", "status": "seen"}, ctx
    )
    logger.info(f"[agent] echo_agent dispatched -> {result}")


def _create_device(container: ServiceContainer, db) -> None:
    from devices.simulated import SimulatedDevice

    device_api = container.get("device_api")
    reasoning_api = container.get("reasoning_api")

    device = SimulatedDevice(device_id="happy_device", ownership_declared=True)
    device.connect()
    device_api.register(device)

    reasoning_api.assert_fact(
        db, subject="happy_device", predicate="event", obj="connected"
    )
    logger.info("[device] registered happy_device (transport=simulated)")


def _store_memory(container: ServiceContainer, db) -> None:
    memory_api = container.get("memory_api")
    entry = memory_api.remember(
        db, "Happy path executed successfully", tag="happy_path", source="demo"
    )
    logger.info(f"[memory] stored entry {entry.id}")


def _query_knowledge_graph(container: ServiceContainer, db) -> None:
    reasoning_api = container.get("reasoning_api")
    facts = reasoning_api.query_facts(db, subject="happy_device")
    logger.info(f"[reasoning] found {len(facts)} fact(s) for happy_device")
    for f in facts:
        logger.info(f"  -> {f.predicate}: {f.object}")


def _build_twin(container: ServiceContainer, db) -> None:
    from digital_twin.twin import build_twin

    twin = build_twin(db, "happy_device")
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
