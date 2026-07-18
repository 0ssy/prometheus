"""CLI subcommands for the Prometheus Engineering Intelligence Platform."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path

from core.bootstrap import boot
from core.commands import dispatch_command
from core.config import config
from core.container import ServiceContainer
from core.database import SessionLocal, create_engine, sessionmaker
from core.logger import get_logger
from services.platform_service import PlatformService

from prometheus_cli.bootstrap import print_banner, print_boot_logo
from prometheus_cli import pack as pack_mod
from prometheus_cli import scaffold

logger = get_logger(__name__)

_KNOWN_SDK_PACKAGES = {
    "robotics": "Robotics control surfaces, kinematics, and actuator drivers.",
    "android": "Android device bridge, ADB tooling, and mobile recovery flows.",
    "cad": "CAD model ingestion and geometry-to-digital-twin conversion.",
    "vision": "Computer-vision pipelines for device inspection and OCR.",
    "drone": "UAV telemetry, flight planning, and failsafe recovery.",
}

_EXTENSIONS_DIR = Path(__file__).resolve().parent.parent.parent / "extensions"
_EXTENSIONS_REGISTRY = _EXTENSIONS_DIR / "registry.json"


def _load_extension_registry() -> dict:
    if _EXTENSIONS_REGISTRY.exists():
        try:
            return json.loads(_EXTENSIONS_REGISTRY.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"installed": []}
    return {"installed": []}


def _save_extension_registry(registry: dict) -> None:
    _EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)
    _EXTENSIONS_REGISTRY.write_text(
        json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8"
    )


def run_install(package: str) -> int:
    package = package.lower()
    if package not in _KNOWN_SDK_PACKAGES:
        logger.error(f"Unknown SDK package: {package}")
        print(f"error: unknown SDK package '{package}'")
        print("available: " + ", ".join(sorted(_KNOWN_SDK_PACKAGES)))
        return 1

    registry = _load_extension_registry()
    installed = {e["name"] for e in registry["installed"]}
    if package in installed:
        print(f"{package} is already installed.")
        return 0

    scaffold = _EXTENSIONS_DIR / package
    scaffold.mkdir(parents=True, exist_ok=True)
    readme = scaffold / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# Prometheus SDK — {package}\n\n"
            f"{_KNOWN_SDK_PACKAGES[package]}\n\n"
            "This extension was scaffolded by `prometheus install`.\n"
            "Implement your capability and register it through the plugin SDK.\n",
            encoding="utf-8",
        )

    registry["installed"].append(
        {
            "name": package,
            "description": _KNOWN_SDK_PACKAGES[package],
            "path": f"extensions/{package}",
            "installed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    _save_extension_registry(registry)
    logger.info(f"Installed SDK package: {package}")
    print(f"installed SDK package: {package}")
    print(f"  -> {scaffold}")
    return 0


def run_extensions() -> int:
    registry = _load_extension_registry()
    installed = registry["installed"]
    if not installed:
        print("no SDK packages installed.")
        print("try: prometheus install robotics")
        return 0
    print("installed SDK packages:")
    for e in installed:
        print(f"  - {e['name']}: {e['description']}")
    return 0


def run_new(kind: str, name: str) -> int:
    if kind == "plugin":
        target = scaffold.scaffold_plugin(name)
    elif kind == "agent":
        target = scaffold.scaffold_agent(name)
    elif kind == "driver":
        target = scaffold.scaffold_driver(name)
    else:
        print(f"unknown scaffold kind: {kind} (expected plugin/agent/driver)")
        return 1

    print(f"scaffolded {kind}: {target}")
    return 0


def run_pack(path: str) -> int:
    try:
        zip_path = pack_mod.pack(path)
    except FileNotFoundError as exc:
        logger.error(str(exc))
        print(f"error: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.error(f"pack failed: {exc}")
        print(f"error: pack failed: {exc}")
        return 1
    print(f"packed: {zip_path}")
    return 0


def run_verify(path: str) -> int:
    result = pack_mod.verify(path)
    if result["ok"]:
        print(f"verified: {path}")
        print(f"  component: {result.get('component')}")
        print(f"  members:   {result.get('member_count')}")
        print(f"  algorithm: {result.get('algorithm')}")
        return 0
    print(f"verification failed: {path}")
    for err in result.get("errors", []):
        print(f"  - {err}")
    return 1


def _status_snapshot(container: ServiceContainer, db) -> dict:
    from sqlalchemy import func
    from knowledge.node import KnowledgeNode
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
        print_banner(snapshot)
        return 0
    finally:
        container.get("scheduler").stop()


def run_demo(db_path: str | None = None) -> dict:
    logger.info("=== HAPPY PATH START ===")
    container = boot(_heartbeat_job)

    if db_path:
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    else:
        engine = None
        SessionFactory = SessionLocal

    try:
        with SessionFactory() as db:
            _run_plugin(container, db)
            _run_agent(container, db)
            _create_device(container, db)
            _store_memory(container, db)
            _query_knowledge_graph(container, db)
            _build_twin(container, db)
            report = _generate_report(container, db)
            report["db_path"] = db_path or str(config.db_path)
    finally:
        container.get("scheduler").stop()
        if engine is not None:
            engine.dispose()

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


def run_full_system(open_browser: bool = True) -> None:
    import uvicorn
    from backend.main import app

    url = f"http://{config.api_host}:{config.api_port}/dashboard"
    health_url = f"http://{config.api_host}:{config.api_port}/health"

    logger.info(f"=== STARTING PROMETHEUS at {url} ===")

    def _wait_and_open():
        start = time.time()
        while time.time() - start < 30:
            try:
                urllib.request.urlopen(health_url, timeout=1)
                if open_browser:
                    webbrowser.open(url)
                print(f"Workspace ready: {url}")
                return
            except Exception:
                time.sleep(0.3)
        print(f"Server did not become ready within timeout. Open manually: {url}")

    threading.Thread(target=_wait_and_open, daemon=True).start()
    print("Starting Prometheus Engineering Intelligence Platform...")
    print(f"Workspace: {url}")
    print("Press Ctrl+C to stop.\n")

    uvicorn.run(
        app,
        host=config.api_host,
        port=config.api_port,
        reload=False,
    )


def run_server() -> None:
    """Headless server mode. Boots the full system, serves the API,
    but never opens a browser window."""
    run_full_system(open_browser=False)


def run_safe() -> None:
    """Safe mode. Boots with minimal services (no plugins/agents)."""
    print_boot_logo(config.version)
    print("Booting in SAFE MODE - minimal services.\n")
    container = boot(_heartbeat_job, safe_mode=True)
    print("Prometheus platform online (safe mode).")
    print("Press Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        container.get("scheduler").stop() if container.get("scheduler") else None
        logger.info("Prometheus stopped")


def run_developer() -> None:
    """Developer workspace. Full system plus a dump of registered
    services so the developer can see the live surface area."""
    print_boot_logo(config.version)
    container = boot(_heartbeat_job)
    print("Developer workspace - registered services:\n")
    for svc in container.list_services():
        print(f"  - {svc}")
    print()
    run_full_system(open_browser=True)


def run_terminal() -> None:
    """Boots the platform and drops into a live Prometheus shell."""
    print_boot_logo(config.version)
    print("Terminal mode - platform online. Type 'help'.\n")
    container = boot(_heartbeat_job)
    platform = container.resolve("platform_service", PlatformService)

    def handler():
        print("Prometheus shell - type 'help'. Ctrl+C or 'exit' to quit.")
        while True:
            try:
                raw = input("prometheus> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nbye.")
                break
            if not raw:
                continue
            if raw in ("exit", "quit"):
                print("bye.")
                break
            _terminal_command(container, platform, raw)

    try:
        handler()
    finally:
        scheduler = container.get("scheduler")
        if scheduler is not None:
            scheduler.stop()
        logger.info("Prometheus terminal mode stopped")


def _terminal_command(container, platform, raw: str) -> None:
    try:
        response = dispatch_command(raw=raw, platform=platform, container=container)
        print(response)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
