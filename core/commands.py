from __future__ import annotations


from core.database import SessionLocal
from core.logger import get_logger

logger = get_logger(__name__)


HELP_TEXT = """commands: status | connect <device> | list devices|agents|plugins | run simulation <device> | search <query> | build digital-twin <device> | dispatch <agent> <task> | show devices|agents|kernel | help"""


def _status_snapshot(container, db) -> dict:
    from sqlalchemy import func
    from knowledge.node import KnowledgeNode
    from reasoning.models import KnowledgeFact

    kernel = container.get("kernel")
    knowledge_engine = container.get("knowledge_engine")
    reasoning_api = container.get("reasoning_api")
    device_api = container.get("device_api")
    plugin_api = container.get("plugin_api")
    capability_api = container.get("capability_api")

    kernel_status = "Running" if kernel.health().get("status") == "ok" else "Stopped"

    knowledge_node_count = db.query(func.count(KnowledgeNode.id)).scalar()
    knowledge_status = "Healthy" if (knowledge_engine is not None and int(knowledge_node_count or 0) > 0) else "Idle"

    simulation_status = "Idle"

    reasoning_status = "Healthy" if reasoning_api is not None else "Idle"

    devices = device_api.list() if device_api is not None else []
    hardware_hal = container.get("hardware_hal")
    hardware_status = "Active" if (hardware_hal is not None and len(devices) > 0) else "Idle"

    agents = container.get("agent_api")
    agent_count = len(agents.list_agents()) if agents is not None else 0

    agent_statuses = []
    if agents is not None and hasattr(agents, "list_agent_statuses"):
        agent_statuses = agents.list_agent_statuses()

    return {
        "kernel": kernel_status,
        "knowledge": knowledge_status,
        "simulation": simulation_status,
        "reasoning": reasoning_status,
        "hardware": hardware_status,
        "devices": len(devices),
        "agents": agent_count,
        "agent_statuses": agent_statuses,
        "plugins": len(plugin_api.list_plugins()) if plugin_api is not None else 0,
        "capabilities": len(capability_api.discover()) if capability_api is not None else 0,
        "knowledge_facts": int(db.query(func.count(KnowledgeFact.id)).scalar() or 0),
    }


def _format_status(snapshot: dict) -> str:
    lines = []
    for k, v in snapshot.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)


def dispatch_command(raw: str, platform, container, db=None) -> str:
    parts = raw.strip().split()
    if not parts:
        return "type 'help' for available commands"

    cmd = parts[0].lower()

    if cmd == "help":
        return HELP_TEXT

    if cmd == "status":
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        try:
            snapshot = _status_snapshot(container, db)
            return _format_status(snapshot)
        finally:
            if close_db:
                db.close()

    if cmd == "connect" and len(parts) >= 2:
        device_id = parts[1]
        result = platform.register_simulated_device(device_id=device_id)
        return f"connected {device_id} ({result.get('transport')})"

    if cmd == "list":
        what = parts[1] if len(parts) > 1 else ""
        items = []
        if what == "devices":
            for d in platform.list_devices():
                items.append(f"  - {d.get('device_id')} ({d.get('transport')})")
        elif what == "agents":
            agent_api = container.get("agent_api")
            for a in agent_api.list_agents():
                items.append(f"  - {a}")
        elif what == "plugins":
            plugin_api = container.get("plugin_api")
            for p in plugin_api.list_plugins():
                items.append(f"  - {p}")
        else:
            return "list what? try: devices | agents | plugins"
        return "\n".join(items) if items else f"no {what} found"

    if cmd == "run" and len(parts) >= 3 and parts[1] == "simulation":
        device_id = parts[2]
        engine = container.get("simulation_engine")
        result = engine.simulate(device_id, {}, "disconnect")
        return f"simulation {device_id}: risk={result.get('risk')} recovered={result.get('recovered')}"

    if cmd == "search" and len(parts) >= 2:
        query = " ".join(parts[1:])
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        try:
            facts = platform.get_facts(db, subject=query)
        finally:
            if close_db:
                db.close()
        if facts:
            return "\n".join(f"  {f.subject} {f.predicate} {f.object}" for f in facts)
        return f"no facts matching '{query}'"

    if cmd == "build" and len(parts) >= 3 and parts[1] == "digital-twin":
        device_id = parts[2]
        from digital_twin.twin import build_twin
        device_api = container.get("device_api")
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        try:
            twin = build_twin(db, device_id, device_api=device_api)
        finally:
            if close_db:
                db.close()
        return f"digital twin {device_id}: state={twin.state} health={twin.health}"

    if cmd == "dispatch" and len(parts) >= 3:
        agent_name = parts[1]
        task = {"description": " ".join(parts[2:])}
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        try:
            result = platform.dispatch_agent(db=db, agent_name=agent_name, task=task)
            return str(result)
        finally:
            if close_db:
                db.close()

    if cmd == "show":
        target = parts[1] if len(parts) > 1 else ""
        if target == "devices":
            return "\n".join(f"  - {d.get('device_id')} ({d.get('transport')})" for d in platform.list_devices())
        if target == "agents":
            agent_api = container.get("agent_api")
            return "\n".join(f"  - {a}" for a in agent_api.list_agents())
        if target == "kernel":
            kernel = container.get("kernel")
            return str(kernel.status())
        return "show what? try: devices | agents | kernel"

    if cmd == "usb" and len(parts) >= 2:
        from sdk.usb import Usb

        client = Usb()
        subcmd = parts[1]
        if subcmd == "list":
            devices = client.enumerate()
            if not devices:
                return "no USB devices detected"
            return "\n".join(
                f"  - {d['device_id']} {d['vid_pid']} {d['manufacturer'] or ''} {d['product'] or ''}".rstrip()
                for d in devices
            )
        if subcmd == "info" and len(parts) >= 3:
            info = client.get(parts[2])
            return str(info) if info else f"unknown device: {parts[2]}"
        if subcmd == "monitor":
            client.start_monitor(interval=1.0)
            return "USB hot-plug monitor started (background thread)"
        return "usb: list | info <device_id> | monitor"

    if cmd == "serial" and len(parts) >= 2:
        from sdk.serial import Serial

        client = Serial()
        subcmd = parts[1]
        if subcmd == "list":
            ports = client.enumerate()
            if not ports:
                return "no serial ports detected"
            return "\n".join(
                f"  - {p['port']} {p.get('vid_pid') or ''} {p.get('manufacturer') or ''} {p.get('product') or ''}".rstrip()
                for p in ports
            )
        if subcmd == "info" and len(parts) >= 3:
            info = client.get(parts[2])
            return str(info) if info else f"unknown port: {parts[2]}"
        if subcmd == "connect" and len(parts) >= 3:
            baud = int(parts[3]) if len(parts) > 3 else 115200
            return str(client.connect(parts[2], baud_rate=baud))
        if subcmd == "disconnect" and len(parts) >= 3:
            return str(client.disconnect(parts[2]))
        if subcmd == "monitor":
            client.start_monitor(interval=1.0)
            return "Serial hot-plug monitor started (background thread)"
        return "serial: list | info <port> | connect <port> [baud] | disconnect <port> | monitor"

    return "unrecognized command. type 'help'."
