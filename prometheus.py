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


# ---------------------------------------------------------------------------
# Z16 — SDK / Extension registry
# ---------------------------------------------------------------------------
# Installed SDK packages are recorded here so the ecosystem can grow without
# touching core. `prometheus install <package>` seeds an extension scaffold.

_KNOWN_SDK_PACKAGES = {
    "robotics": "Robotics control surfaces, kinematics, and actuator drivers.",
    "android": "Android device bridge, ADB tooling, and mobile recovery flows.",
    "cad": "CAD model ingestion and geometry-to-digital-twin conversion.",
    "vision": "Computer-vision pipelines for device inspection and OCR.",
    "drone": "UAV telemetry, flight planning, and failsafe recovery.",
}

_EXTENSIONS_DIR = Path(_REPO_ROOT) / "extensions"
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


_BOOT_LOGO = """  ____  ____  ____  ____  ____  ____  __  __  _____
 |  _ \\|  _ \\|  _ \\|  _ \\|  _ \\|  _ \\|  \\/  \\/  __  |
 | |_) | |_) | |_) | |_) | |_) | |_) | |\\/| | |  | |
 |  __/|  __/|  __/|  __/|  __/|  __/| |  | | |__| |
 |_|   |_|   |_|   |_|   |_|   |_|   |_|  |_|\\_____/"""


def _print_boot_logo(version: str) -> None:
    print()
    print(_BOOT_LOGO)
    print("Engineering Intelligence OS")
    print(f"v{version}")
    print()


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
    print("Starting Prometheus Engineering OS...")
    print(f"Workspace: {url}")
    print("Press Ctrl+C to stop.\n")

    uvicorn.run(
        app,
        host=config.api_host,
        port=config.api_port,
        reload=False,
    )


def run_server() -> None:
    """Z15 — Headless server mode. Boots the full system, serves the API,
    but never opens a browser window."""
    run_full_system(open_browser=False)


def run_safe() -> None:
    """Z15 — Safe mode. Boots with minimal services (no plugins/agents)."""
    _print_boot_logo(config.version)
    print("Booting in SAFE MODE - minimal services.\n")
    container = boot(_heartbeat_job, safe_mode=True)
    print("Prometheus kernel online (safe mode).")
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
    """Z15 — Developer workspace. Full system plus a dump of registered
    services so the developer can see the live surface area."""
    _print_boot_logo(config.version)
    container = boot(_heartbeat_job)
    print("Developer workspace - registered services:\n")
    for svc in container.list_services():
        print(f"  - {svc}")
    print()
    run_full_system(open_browser=True)


# ---------------------------------------------------------------------------
# Z15 — Terminal only mode
# ---------------------------------------------------------------------------


def run_terminal() -> None:
    """`prometheus --terminal` — boots the kernel and drops into a live
    Prometheus shell. Every command maps to the same platform services the
    GUI uses, so the CLI and the desktop stay in lock-step."""
    _print_boot_logo(config.version)
    print("Terminal mode - kernel online. Type 'help'.\n")
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
    parts = raw.split()
    cmd = parts[0].lower()
    try:
        if cmd == "help":
            print(
                "commands: status | connect <device> | list devices|agents|plugins "
                "| run simulation <device> | search <query> | build digital-twin <device> "
                "| open <app> | exit"
            )
        elif cmd == "status":
            with SessionLocal() as db:
                snapshot = _status_snapshot(container, db)
            _print_banner(snapshot)
        elif cmd == "connect" and len(parts) >= 2:
            device_id = parts[1]
            result = platform.register_simulated_device(device_id=device_id)
            print(f"connected {device_id} ({result.get('transport')})")
        elif cmd == "list":
            _terminal_list(container, platform, parts[1] if len(parts) > 1 else "")
        elif cmd == "run" and len(parts) >= 3 and parts[1] == "simulation":
            device_id = parts[2]
            engine = container.get("simulation_engine")
            result = engine.simulate(device_id, {}, "disconnect")
            print(f"simulation {device_id}: risk={result.get('risk')} "
                  f"recovered={result.get('recovered')}")
        elif cmd == "search" and len(parts) >= 2:
            query = " ".join(parts[1:])
            with SessionLocal() as db:
                facts = platform.get_facts(db, subject=query)
            if facts:
                for f in facts:
                    print(f"  {f.subject} {f.predicate} {f.object}")
            else:
                print(f"no facts matching '{query}'")
        elif cmd == "build" and len(parts) >= 3 and parts[1] == "digital-twin":
            from digital_twin.twin import build_twin

            device_id = parts[2]
            with SessionLocal() as db:
                twin = build_twin(db, device_id, device_api=container.get("device_api"))
            print(f"digital twin {device_id}: state={twin.state} health={twin.health}")
        elif cmd == "open":
            print("'open' launches a desktop application — available in desktop mode "
                  "(run `prometheus` without --terminal).")
        else:
            print("unrecognized command. type 'help'.")
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")


def _terminal_list(container, platform, what: str) -> None:
    if what == "devices":
        for d in platform.list_devices():
            print(f"  - {d.get('device_id')} ({d.get('transport')})")
    elif what == "agents":
        agent_api = container.get("agent_api")
        for a in agent_api.list_agents():
            print(f"  - {a}")
    elif what == "plugins":
        plugin_api = container.get("plugin_api")
        for p in plugin_api.list_plugins():
            print(f"  - {p}")
    else:
        print("list what? try: devices | agents | plugins")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="prometheus",
        description="Prometheus Engineering Intelligence OS — unified entry point",
    )
    parser.add_argument(
        "--terminal", action="store_true",
        help="terminal-only mode: boot the kernel and drop into a live shell",
    )
    parser.add_argument(
        "--developer", action="store_true",
        help="developer workspace: full system + registered service dump",
    )
    parser.add_argument(
        "--server", action="store_true",
        help="headless server mode: serve the API, never open a browser",
    )
    parser.add_argument(
        "--safe-mode", action="store_true",
        help="boot with minimal services (no plugins/agents)",
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="print branded platform status banner")
    sub.add_parser("demo", help="run happy-path demo")
    install_parser = sub.add_parser("install", help="install an SDK package (robotics/android/cad/vision/drone)")
    install_parser.add_argument("package", help="SDK package name to install")
    sub.add_parser("extensions", help="list installed SDK packages")
    test_parser = sub.add_parser("test", help="run pytest suite")
    test_parser.add_argument("--file", default=None, help="optional test file/directory")

    args = parser.parse_args()

    if args.command == "install":
        return run_install(args.package)
    if args.command == "extensions":
        return run_extensions()

    if not args.command:
        if args.terminal:
            run_terminal()
            return 0
        if args.developer:
            run_developer()
            return 0
        if args.server:
            run_server()
            return 0
        if args.safe_mode:
            run_safe()
            return 0
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
