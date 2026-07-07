#!/usr/bin/env python3
"""
Prometheus — Unified Platform Entry Point
-----------------------------------------
Runs the entire system from one file:
  - bootstrap + runtime
  - FastAPI web server
  - happy-path demo
  - test runner

Usage:
  python prometheus.py runtime
  python prometheus.py api
  python prometheus.py demo
  python prometheus.py test
  python prometheus.py test --file tests/test_epsilon_service.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

from core.bootstrap import boot
from core.config import config
from core.container import ServiceContainer
from core.database import SessionLocal
from core.logger import get_logger
from services.platform_service import PlatformService


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------

def _heartbeat_job() -> None:
    logger.info("Prometheus heartbeat — platform runtime alive")


def run_runtime() -> ServiceContainer:
    logger.info("=== BOOTSTRAP RUNTIME ===")
    container = boot(_heartbeat_job)
    logger.info("Platform started — press Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        container.get("scheduler").stop()
        logger.info("Platform stopped")
    return container


# ---------------------------------------------------------------------------
# FastAPI server
# ---------------------------------------------------------------------------

def run_api() -> None:
    import uvicorn
    logger.info("=== STARTING API SERVER ===")
    uvicorn.run(
        "backend.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=True,
    )


# ---------------------------------------------------------------------------
# Happy path demo
# ---------------------------------------------------------------------------

def run_demo() -> dict:
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
    result = platform.run_plugin(db, plugin_name="echo", payload={"message": "hello from prometheus"})
    logger.info(f"[plugin] {result}")


def _run_agent(container: ServiceContainer, db) -> None:
    platform = container.resolve("platform_service", PlatformService)
    result = platform.dispatch_agent(db, "echo_agent", {"device_id": "demo_device", "status": "seen"})
    logger.info(f"[agent] {result}")


def _create_device(container: ServiceContainer, db) -> None:
    platform = container.resolve("platform_service", PlatformService)
    result = platform.register_simulated_device(device_id="demo_device", ownership_declared=True)
    logger.info(f"[device] registered {result['device_id']} ({result['transport']})")


def _store_memory(container: ServiceContainer, db) -> None:
    platform = container.resolve("platform_service", PlatformService)
    entry = platform.store_memory(db, "Demo executed successfully", tag="demo", source="cli")
    logger.info(f"[memory] stored entry {entry.id}")


def _query_knowledge_graph(container: ServiceContainer, db) -> None:
    platform = container.resolve("platform_service", PlatformService)
    facts = platform.get_facts(db, subject="demo_device")
    logger.info(f"[knowledge] found {len(facts)} fact(s) for demo_device")
    for f in facts:
        logger.info(f"  -> {f.predicate}: {f.object}")


def _build_twin(container: ServiceContainer, db) -> None:
    from digital_twin.twin import build_twin
    twin = build_twin(db, "demo_device", device_api=container.get("device_api"))
    logger.info(f"[twin] built twin for demo_device: state={twin.state}, health={twin.health}")


def _generate_report(container: ServiceContainer, db) -> dict:
    from sqlalchemy import func
    from memory.models import MemoryEntry
    from reasoning.models import KnowledgeFact

    memory_count = db.query(func.count(MemoryEntry.id)).scalar()
    fact_count = db.query(func.count(KnowledgeFact.id)).scalar()

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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_tests(path: str | None = None) -> int:
    cmd = [sys.executable, "-m", "pytest", "-q"]
    if path:
        cmd.append(path)
    logger.info(f"[test] running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="prometheus",
        description="Prometheus platform unified entry point",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("runtime", help="run platform runtime (blocks until Ctrl+C)")
    sub.add_parser("api", help="start FastAPI web server")
    sub.add_parser("demo", help="run happy-path demo")
    test_parser = sub.add_parser("test", help="run pytest suite")
    test_parser.add_argument("--file", default=None, help="optional test file/directory")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "runtime":
        run_runtime()
        return 0
    if args.command == "api":
        run_api()
        return 0
    if args.command == "demo":
        run_demo()
        return 0
    if args.command == "test":
        return run_tests(args.file)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
