#!/usr/bin/env python3
"""
Prometheus — Unified Platform Entry Point
-----------------------------------------
Runs the entire system from one file:
  - bootstrap + runtime
  - FastAPI web server + dashboard
  - happy-path demo
  - test runner
  - status report (branded banner)

Usage:
  python prometheus.py                      # start full system + dashboard
  python prometheus.py status               # print branded status banner
  python prometheus.py demo                 # run happy-path demo
  python prometheus.py test
  python prometheus.py test --file tests/test_epsilon_service.py
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
import webbrowser

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.bootstrap import boot
from core.config import config
from core.container import ServiceContainer
from core.database import SessionLocal
from core.logger import get_logger
from services.platform_service import PlatformService


logger = get_logger(__name__)


_LABEL_WIDTH = 21


def _banner_line(label: str, value: str) -> str:
    return f"{label:<{_LABEL_WIDTH}}{value}"


def _print_banner(snapshot: dict) -> None:
    print()
    print("Prometheus Engineering OS")
    print(f"Version {config.version}")
    print()

    print(_banner_line("Kernel", snapshot["kernel"]))
    print(_banner_line("Knowledge", snapshot["knowledge"]))
    print(_banner_line("Simulation", snapshot["simulation"]))
    print(_banner_line("Reasoning", snapshot["reasoning"]))
    print(_banner_line("Hardware", snapshot["hardware"]))
    print()
    print(_banner_line("Connected Devices", str(snapshot["devices"])))
    print(_banner_line("Agents", str(snapshot["agents"])))
    print(_banner_line("Plugins", str(snapshot["plugins"])))
    print(_banner_line("Capabilities", str(snapshot["capabilities"])))
    print(_banner_line("Knowledge Facts", str(snapshot["knowledge_facts"])))
    print()
    print("Ready.")
    print()


def _status_snapshot(container: ServiceContainer, db) -> dict:
    from sqlalchemy import func
    from knowledge.node import KnowledgeNode
    from memory.models import MemoryEntry
    from reasoning.models import KnowledgeFact

    kernel = container.get("kernel")
    knowledge_engine = container.get("knowledge_engine")
    reasoning_api = container.get("reasoning_api")
    device_api = container.get("device_api")
    plugin_api = container.get("plugin_api")
    agent_api = container.get("agent_api")
    capability_api = container.get("capability_api")

    kernel_status = "Running" if kernel.health().get("status") == "ok" else "Stopped"

    knowledge_node_count = db.query(func.count(KnowledgeNode.id)).scalar()
    knowledge_status = "Healthy" if (knowledge_engine is not None and int(knowledge_node_count or 0) > 0) else "Idle"

    simulation_status = "Idle"

    reasoning_status = "Healthy" if reasoning_api is not None else "Idle"

    devices = device_api.list() if device_api is not None else []
    hardware_hal = container.get("hardware_hal")
    hardware_status = "Active" if (hardware_hal is not None and len(devices) > 0) else "Idle"

    return {
        "kernel": kernel_status,
        "knowledge": knowledge_status,
        "simulation": simulation_status,
        "reasoning": reasoning_status,
        "hardware": hardware_status,
        "devices": len(devices),
        "agents": len(agent_api.list_agents()) if agent_api is not None else 0,
        "plugins": len(plugin_api.list_plugins()) if plugin_api is not None else 0,
        "capabilities": len(capability_api.discover()) if capability_api is not None else 0,
        "knowledge_facts": int(db.query(func.count(KnowledgeFact.id)).scalar() or 0),
    }


def _heartbeat_job() -> None:
    logger.info("Prometheus heartbeat — platform runtime alive")


def run_status() -> int:
    container = boot(_heartbeat_job)
    try:
        with SessionLocal() as db:
            snapshot = _status_snapshot(container, db)
        _print_banner(snapshot)
        return 0
    finally:
        container.get("scheduler").stop()


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


def run_tests(path: str | None = None) -> int:
    cmd = [sys.executable, "-m", "pytest", "-q"]
    if path:
        cmd.append(path)
    logger.info(f"[test] running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def run_full_system() -> None:
    import uvicorn

    url = f"http://{config.api_host}:{config.api_port}/dashboard"
    health_url = f"http://{config.api_host}:{config.api_port}/health"

    logger.info(f"=== STARTING PROMETHEUS at {url} ===")

    def _wait_and_open():
        start = time.time()
        while time.time() - start < 30:
            try:
                urllib.request.urlopen(health_url, timeout=1)
                webbrowser.open(url)
                print(f"Dashboard ready: {url}")
                return
            except Exception:
                time.sleep(0.3)
        print(f"Server did not become ready within timeout. Open manually: {url}")

    threading.Thread(target=_wait_and_open, daemon=True).start()
    print("Starting Prometheus Engineering OS...")
    print(f"Dashboard: {url}")
    print("Press Ctrl+C to stop.\n")

    uvicorn.run(
        "backend.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="prometheus",
        description="Prometheus platform unified entry point",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="print branded platform status banner")
    sub.add_parser("demo", help="run happy-path demo")
    test_parser = sub.add_parser("test", help="run pytest suite")
    test_parser.add_argument("--file", default=None, help="optional test file/directory")

    args = parser.parse_args()

    if not args.command:
        run_full_system()
        return 0

    if args.command == "status":
        return run_status()
    if args.command == "demo":
        run_demo()
        return 0
    if args.command == "test":
        return run_tests(args.file)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
