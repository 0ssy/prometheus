"""
Prometheus Local API — Entry Point
-----------------------------------------
Run with: uvicorn backend.main:app --reload
(run from the prometheus/ root directory)

All subsystems are wired through the ServiceContainer bootstrapped
at startup. Endpoints access services via the container rather than
direct imports.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue

from fastapi import FastAPI, Depends, Body, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.config import config
from core.logger import get_logger
from core.database import get_db
from core.bootstrap import boot
from core.container import ServiceContainer
from services.platform_service import PlatformService
from services.delta_service import DeltaService
from services.epsilon_service import EpsilonService
from services.omega_service import OmegaService
from core.ownership_registry import (
    declare_owned,
    is_declared_owned,
    revoke_declaration,
    list_declared,
)

logger = get_logger(__name__)

app = FastAPI(title=config.app_name, version=config.version)

_container: ServiceContainer | None = None


def get_container() -> ServiceContainer:
    if _container is None:
        raise RuntimeError("Platform not bootstrapped — container is None")
    return _container


def _heartbeat_job():
    logger.info("Prometheus heartbeat — system alive")


def get_platform_service(
    container: ServiceContainer = Depends(get_container),
) -> PlatformService:
    return container.resolve("platform_service", PlatformService)


def get_delta_service(
    container: ServiceContainer = Depends(get_container),
) -> DeltaService:
    return container.resolve("delta_service", DeltaService)


def get_epsilon_service(
    container: ServiceContainer = Depends(get_container),
) -> EpsilonService:
    return container.resolve("epsilon_service", EpsilonService)


def get_omega_service(
    container: ServiceContainer = Depends(get_container),
) -> OmegaService:
    return container.resolve("omega_service", OmegaService)


@app.on_event("startup")
def startup():
    global _container
    _container = boot(_heartbeat_job)
    app.state.container = _container
    logger.info("Backend ready — services available via app.state.container")


from backend.dashboard import mount_dashboard

mount_dashboard(app)


@app.get("/health")
def health(container: ServiceContainer = Depends(get_container)):
    plugin_api = container.get("plugin_api")
    agent_api = container.get("agent_api")
    capability_api = container.get("capability_api")
    kernel = container.get("kernel")
    return {
        "status": "ok",
        "app": config.app_name,
        "version": config.version,
        "plugins_loaded": plugin_api.list_plugins(),
        "agents_loaded": agent_api.list_agents(),
        "capabilities_registered": len(capability_api.discover()),
        "kernel_health": kernel.health(),
    }


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


@app.get("/status")
def platform_status(container: ServiceContainer = Depends(get_container), db: Session = Depends(get_db)):
    return _status_snapshot(container, db)


@app.get("/stats")
def platform_stats(container: ServiceContainer = Depends(get_container), db: Session = Depends(get_db)):
    from sqlalchemy import func
    from memory.models import MemoryEntry
    from reasoning.models import KnowledgeFact
    from knowledge.node import KnowledgeNode

    return {
        "devices": len(container.get("device_api").list()),
        "agents": len(container.get("agent_api").list_agents()),
        "plugins": len(container.get("plugin_api").list_plugins()),
        "capabilities": len(container.get("capability_api").discover()),
        "knowledge_nodes": int(db.query(func.count(KnowledgeNode.id)).scalar() or 0),
        "facts": int(db.query(func.count(KnowledgeFact.id)).scalar() or 0),
        "memory_entries": int(db.query(func.count(MemoryEntry.id)).scalar() or 0),
    }


@app.get("/events")
async def event_stream(container: ServiceContainer = Depends(get_container)):
    event_bus = container.get("event_bus")
    queue: Queue = Queue()

    event_types = [
        "plugin.ran",
        "agent.dispatched",
        "agent.status",
        "device.connected",
        "device.disconnected",
        "device.connect_failed",
        "device.wrote",
        "memory.stored",
        "fact.asserted",
        "capability.executed",
    ]

    def handler(event):
        queue.put(event)

    for et in event_types:
        event_bus.subscribe(et, handler)

    async def generate():
        loop = asyncio.get_event_loop()
        try:
            while True:
                event = await loop.run_in_executor(None, queue.get)
                payload = {
                    "type": event.event_type,
                    "timestamp": event.timestamp.isoformat(),
                    "data": {k: v for k, v in event.__dict__.items() if k not in ("event_type", "timestamp")},
                }
                yield f"data: {json.dumps(payload)}\n\n"
        finally:
            for et in event_types:
                event_bus.unsubscribe(et, handler)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/system/services")
def list_services(container: ServiceContainer = Depends(get_container)):
    return {"services": container.list_services()}


@app.get("/capabilities")
def list_capabilities(
    prefix: str | None = None,
    target: str | None = None,
    platform: PlatformService = Depends(get_platform_service),
):
    return {"capabilities": platform.list_capabilities(prefix=prefix, target=target)}


@app.post("/capabilities/execute")
def execute_capability(
    name: str,
    payload: dict | None = None,
    permissions: list[str] | None = None,
    platform: PlatformService = Depends(get_platform_service),
):
    result = platform.execute_capability(
        capability_name=name,
        payload=payload or {},
        granted_permissions=set(permissions or []),
    )
    return {"capability": name, "result": result}


@app.get("/capabilities/history")
def capability_history(
    name: str | None = None,
    platform: PlatformService = Depends(get_platform_service),
):
    return {"history": platform.capability_history(capability_name=name)}


@app.get("/core/status")
def core_status(container: ServiceContainer = Depends(get_container)):
    kernel = container.get("kernel")
    return {"status": kernel.status(), "health": kernel.health()}


@app.get("/observability")
def observability_snapshot(container: ServiceContainer = Depends(get_container)):
    observability = container.get("observability")
    return observability.snapshot()


@app.post("/plugins/{plugin_name}/run")
def run_plugin(
    plugin_name: str,
    payload: dict,
    db: Session = Depends(get_db),
    platform: PlatformService = Depends(get_platform_service),
):
    return platform.run_plugin(db, plugin_name=plugin_name, payload=payload)


@app.post("/agents/{agent_name}/dispatch")
def dispatch_agent(
    agent_name: str,
    task: dict,
    db: Session = Depends(get_db),
    platform: PlatformService = Depends(get_platform_service),
):
    return platform.dispatch_agent(db, agent_name=agent_name, task=task)


@app.post("/memory")
def store_memory(
    content: str,
    tag: str = "general",
    db: Session = Depends(get_db),
    platform: PlatformService = Depends(get_platform_service),
):
    entry = platform.store_memory(db, content=content, tag=tag, source="api")
    return {"id": entry.id, "content": entry.content, "tag": entry.tag}


@app.get("/memory")
def get_memory(
    tag: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    platform: PlatformService = Depends(get_platform_service),
):
    entries = platform.get_memory(db, tag=tag, limit=limit)
    return [
        {
            "id": e.id,
            "content": e.content,
            "tag": e.tag,
            "created_at": str(e.created_at),
        }
        for e in entries
    ]


@app.post("/knowledge")
def store_fact(
    subject: str,
    predicate: str,
    object: str,
    db: Session = Depends(get_db),
    platform: PlatformService = Depends(get_platform_service),
):
    fact = platform.store_fact(db, subject=subject, predicate=predicate, obj=object)
    return {
        "id": fact.id,
        "subject": fact.subject,
        "predicate": fact.predicate,
        "object": fact.object,
    }


@app.get("/knowledge")
def get_facts(
    subject: str | None = None,
    db: Session = Depends(get_db),
    platform: PlatformService = Depends(get_platform_service),
):
    facts = platform.get_facts(db, subject=subject)
    return [
        {"subject": f.subject, "predicate": f.predicate, "object": f.object}
        for f in facts
    ]


# ---------------------------------------------------------------------------
# Phase Beta — Devices (RFC 0001)
# ---------------------------------------------------------------------------


@app.post("/devices/simulated")
def register_simulated_device(
    device_id: str,
    latency_seconds: float = 0.0,
    failure_rate: float = 0.0,
    ownership_declared: bool = True,
    platform: PlatformService = Depends(get_platform_service),
):
    return platform.register_simulated_device(
        device_id=device_id,
        latency_seconds=latency_seconds,
        failure_rate=failure_rate,
        ownership_declared=ownership_declared,
    )


@app.post("/devices/serial")
def register_serial_device(
    device_id: str,
    port: str,
    baudrate: int = 115200,
    ownership_declared: bool = False,
    platform: PlatformService = Depends(get_platform_service),
):
    try:
        return platform.register_serial_device(
            device_id=device_id,
            port=port,
            baudrate=baudrate,
            ownership_declared=ownership_declared,
        )
    except Exception:
        logger.exception(f"Failed to connect serial device {device_id}")
        raise


@app.get("/devices")
def list_devices(platform: PlatformService = Depends(get_platform_service)):
    return platform.list_devices()


@app.get("/devices/{device_id}")
def get_device(device_id: str, platform: PlatformService = Depends(get_platform_service)):
    device = platform.get_device(device_id)
    if device is None:
        raise RuntimeError(f"No such device: {device_id}")
    return {
        "device_id": device.device_id,
        "transport": device.transport,
        **device.status(),
    }


@app.post("/devices/{device_id}/write")
def write_device(
    device_id: str,
    payload: dict,
    platform: PlatformService = Depends(get_platform_service),
):
    value = payload.get("value")
    return platform.write_device(device_id=device_id, value=value)


@app.post("/devices/{device_id}/disconnect")
def disconnect_device(
    device_id: str,
    platform: PlatformService = Depends(get_platform_service),
):
    return platform.disconnect_device(device_id=device_id)


# ---------------------------------------------------------------------------
# Ownership (RFC 0000)
# ---------------------------------------------------------------------------


@app.post("/ownership/declare")
def declare_ownership(
    target_id: str,
    note: str = "",
    owner: str = "",
    trust_level: str = "declared",
    keys: list[str] | None = None,
    certificates: list[str] | None = None,
    recovery_policy: str | None = None,
    db: Session = Depends(get_db),
    container: ServiceContainer = Depends(get_container),
):
    reasoning_api = container.get("reasoning_api")
    parsed_recovery_policy = None
    if recovery_policy is not None:
        try:
            parsed_recovery_policy = json.loads(recovery_policy)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid recovery_policy JSON: {e.msg}") from e
    entry = declare_owned(
        target_id,
        note=note,
        owner=owner,
        trust_level=trust_level,
        keys=keys,
        certificates=certificates,
        recovery_policy=parsed_recovery_policy,
    )
    reasoning_api.assert_fact(
        db, subject=target_id, predicate="event", obj="ownership_declared"
    )
    return entry


@app.get("/ownership")
def list_ownership():
    return list_declared()


@app.delete("/ownership/{target_id:path}")
def revoke_ownership(
    target_id: str,
    db: Session = Depends(get_db),
    container: ServiceContainer = Depends(get_container),
):
    reasoning_api = container.get("reasoning_api")
    removed = revoke_declaration(target_id)
    if removed:
        reasoning_api.assert_fact(
            db, subject=target_id, predicate="event", obj="ownership_revoked"
        )
    return {"target_id": target_id, "revoked": removed}


# ---------------------------------------------------------------------------
# Phase Gamma — Partition Mapper (RFC 0002)
# ---------------------------------------------------------------------------


@app.get("/gamma/partitions")
def get_partitions(
    disk_path: str,
    db: Session = Depends(get_db),
    container: ServiceContainer = Depends(get_container),
):
    if not is_declared_owned(disk_path):
        raise HTTPException(
            status_code=403,
            detail=(
                f"{disk_path} is not in your declared-owned devices list. "
                f"Declare it first: POST /ownership/declare?target_id={disk_path}&note=..."
            ),
        )
    try:
        from engineering.partition_mapper import read_partition_table

        table = read_partition_table(disk_path, ownership_declared=True)
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail="OS denied access to this disk — on Windows, try running your terminal as Administrator.",
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No such disk path: {disk_path}")

    reasoning_api = container.get("reasoning_api")
    reasoning_api.assert_fact(
        db,
        subject=disk_path,
        predicate="event",
        obj=f"partition_table_read:{table.scheme}",
    )
    return table.to_dict()


@app.get("/gamma/firmware")
def get_firmware_report(
    path: str,
    db: Session = Depends(get_db),
    container: ServiceContainer = Depends(get_container),
):
    if not is_declared_owned(path):
        raise HTTPException(
            status_code=403,
            detail=(
                f"{path} is not in your declared-owned devices list. "
                f"Declare it first: POST /ownership/declare?target_id={path}&note=..."
            ),
        )
    try:
        from engineering.firmware_inspector import inspect_firmware

        report = inspect_firmware(path, ownership_declared=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No such file: {path}")

    reasoning_api = container.get("reasoning_api")
    reasoning_api.assert_fact(
        db, subject=path, predicate="event", obj=f"firmware_inspected:{report.format}"
    )
    return report.to_dict()


@app.get("/gamma/simulate/{scenario}")
def run_gamma_simulation(
    scenario: str,
    db: Session = Depends(get_db),
    container: ServiceContainer = Depends(get_container),
):
    if scenario not in ("valid", "tampered"):
        raise RuntimeError("scenario must be 'valid' or 'tampered'")

    from engineering.device_simulator import SimulatedFirmwareDevice
    from engineering.boot_chain import analyze_boot_chain
    from engineering.recovery_planner import plan_recovery

    reasoning_api = container.get("reasoning_api")

    device = SimulatedFirmwareDevice(
        f"sim_{scenario}", tampered=(scenario == "tampered")
    )
    boot_result = analyze_boot_chain(
        device.firmware_bytes, device.signature, device.public_key_bytes
    )
    plan = plan_recovery(
        device.device_id, boot_chain_status=boot_result.status, partition_scheme="gpt"
    )

    reasoning_api.assert_fact(
        db,
        subject=device.device_id,
        predicate="event",
        obj=f"boot_chain:{boot_result.status}",
    )

    return {
        "device_id": device.device_id,
        "boot_chain_result": boot_result.to_dict(),
        "recovery_plan": plan.to_dict(),
    }


# ---------------------------------------------------------------------------
# Phase Delta — Digital Twin Engine (RFC 0003)
# ---------------------------------------------------------------------------


@app.get("/delta/twin/{device_id}")
def get_device_twin(
    device_id: str,
    db: Session = Depends(get_db),
    container: ServiceContainer = Depends(get_container),
):
    from digital_twin.twin import build_twin

    device_api = container.get("device_api")
    twin = build_twin(db, device_id, device_api=device_api)
    return twin.to_dict()


# ---------------------------------------------------------------------------
# Phase Beta — Atlas Intelligence Layer
# ---------------------------------------------------------------------------


@app.get("/beta/digital-device/{device_id}")
def get_beta_digital_device(
    device_id: str,
    db: Session = Depends(get_db),
    platform: PlatformService = Depends(get_platform_service),
):
    return platform.digital_device(db, device_id)


@app.post("/beta/workflow/{device_id}")
def run_beta_workflow(
    device_id: str,
    failure_mode: str = "disconnect",
    execute: bool = False,
    permissions: list[str] | None = None,
    db: Session = Depends(get_db),
    platform: PlatformService = Depends(get_platform_service),
):
    return platform.run_beta_workflow(
        db=db,
        device_id=device_id,
        failure_mode=failure_mode,
        execute=execute,
        permissions=set(permissions or []),
    )


# ---------------------------------------------------------------------------
# Phase Gamma - Helios Knowledge Layer
# ---------------------------------------------------------------------------


@app.get("/gamma/knowledge/devices-supporting-recovery")
def gamma_devices_supporting_recovery(
    platform: PlatformService = Depends(get_platform_service),
):
    return {"devices": platform.query_devices_supporting_recovery()}


@app.get("/gamma/knowledge/simulations-failed")
def gamma_simulations_failed(platform: PlatformService = Depends(get_platform_service)):
    return {"simulations": platform.query_simulations_failed()}


@app.get("/gamma/knowledge/capabilities-never-executed")
def gamma_capabilities_never_executed(
    platform: PlatformService = Depends(get_platform_service),
):
    return {"capabilities": platform.query_capabilities_never_executed()}


@app.get("/gamma/knowledge/plugins-for-recommendation")
def gamma_plugins_for_recommendation(
    recommendation_key: str,
    platform: PlatformService = Depends(get_platform_service),
):
    return {
        "plugins": platform.query_plugins_for_recommendation(
            recommendation_key=recommendation_key
        )
    }


@app.get("/gamma/learning")
def gamma_learning(
    scenario_key: str | None = None,
    platform: PlatformService = Depends(get_platform_service),
):
    return {"learning": platform.learning_history(scenario_key=scenario_key)}


# ---------------------------------------------------------------------------
# Phase Delta - Daedalus
# ---------------------------------------------------------------------------


@app.post("/delta/lab/workspaces/{workspace_id}")
def delta_create_workspace(
    workspace_id: str,
    device_count: int = 1,
    delta: DeltaService = Depends(get_delta_service),
):
    return delta.create_workspace(workspace_id=workspace_id, device_count=device_count)


@app.post("/delta/lab/workspaces/{workspace_id}/failures")
def delta_inject_failure(
    workspace_id: str,
    failure_type: str,
    delta: DeltaService = Depends(get_delta_service),
):
    return delta.inject_failure(workspace_id=workspace_id, failure_type=failure_type)


@app.post("/delta/scenarios/{workspace_id}")
def delta_run_scenario(
    workspace_id: str,
    steps: list[str],
    delta: DeltaService = Depends(get_delta_service),
):
    return delta.run_scenario(workspace_id=workspace_id, steps=steps)


@app.get("/delta/time/battery-forecast")
def delta_battery_forecast(
    current_health: float,
    months: int,
    monthly_degradation: float = 0.01,
    delta: DeltaService = Depends(get_delta_service),
):
    return delta.forecast_battery(
        current_health=current_health,
        months=months,
        monthly_degradation=monthly_degradation,
    )


# ---------------------------------------------------------------------------
# Phase Epsilon - Hephaestus
# ---------------------------------------------------------------------------


@app.post("/epsilon/hal/register-defaults")
def epsilon_register_defaults(epsilon: EpsilonService = Depends(get_epsilon_service)):
    return epsilon.register_default_interfaces()


@app.get("/epsilon/hal/interfaces")
def epsilon_list_interfaces(epsilon: EpsilonService = Depends(get_epsilon_service)):
    return epsilon.list_interfaces()


@app.post("/epsilon/connect/{device_id}")
def epsilon_connect_device(
    device_id: str,
    driver_name: str = "virtual",
    epsilon: EpsilonService = Depends(get_epsilon_service),
):
    return epsilon.connect_device(device_id=device_id, driver_name=driver_name)


@app.post("/epsilon/disconnect/{device_id}")
def epsilon_disconnect_device(
    device_id: str,
    epsilon: EpsilonService = Depends(get_epsilon_service),
):
    return epsilon.disconnect_device(device_id=device_id)


@app.get("/epsilon/diagnostics/{device_id}")
def epsilon_device_diagnostics(
    device_id: str, epsilon: EpsilonService = Depends(get_epsilon_service)
):
    return epsilon.diagnostics(device_id=device_id)


@app.get("/epsilon/diagnostics/{device_id}/full")
def epsilon_full_diagnostics(
    device_id: str, epsilon: EpsilonService = Depends(get_epsilon_service)
):
    return epsilon.full_diagnostics(device_id=device_id)


@app.post("/epsilon/recovery/{device_id}")
def epsilon_recovery_plan(
    device_id: str,
    risk: str = "high",
    epsilon: EpsilonService = Depends(get_epsilon_service),
):
    return epsilon.recovery_plan(device_id=device_id, risk=risk)


@app.post("/epsilon/firmware/summary")
def epsilon_firmware_summary(
    metadata: dict,
    epsilon: EpsilonService = Depends(get_epsilon_service),
):
    return epsilon.firmware_summary(metadata=metadata)


@app.post("/epsilon/firmware/parse")
def epsilon_firmware_parse(
    data: bytes,
    epsilon: EpsilonService = Depends(get_epsilon_service),
):
    return epsilon._firmware.parse(data)


# ---------------------------------------------------------------------------
# Phase Omega - Olympus
# ---------------------------------------------------------------------------


@app.post("/omega/marketplace/plugins")
def omega_publish_plugin(
    plugin: dict, omega: OmegaService = Depends(get_omega_service)
):
    return omega.publish_plugin(plugin)


@app.get("/omega/marketplace/plugins")
def omega_list_plugins(omega: OmegaService = Depends(get_omega_service)):
    return {"plugins": omega.list_plugins()}


@app.post("/omega/collaboration/plan")
def omega_collaboration_plan(
    tasks: list[str], omega: OmegaService = Depends(get_omega_service)
):
    return omega.plan_collaboration(tasks)


@app.post("/omega/distributed/nodes/{node_id}")
def omega_register_node(node_id: str, omega: OmegaService = Depends(get_omega_service)):
    return omega.register_node(node_id=node_id)


@app.get("/omega/distributed/nodes")
def omega_list_nodes(omega: OmegaService = Depends(get_omega_service)):
    return omega.list_nodes()


@app.post("/omega/policy/grant")
def omega_grant_policy(
    actor: str, permission: str, omega: OmegaService = Depends(get_omega_service)
):
    return omega.grant_permission(actor=actor, permission=permission)


@app.get("/omega/policy/check")
def omega_check_policy(
    actor: str, permission: str, omega: OmegaService = Depends(get_omega_service)
):
    return omega.check_permission(actor=actor, permission=permission)


@app.get("/omega/public-apis")
def omega_public_apis(omega: OmegaService = Depends(get_omega_service)):
    return omega.public_apis()


@app.post("/omega/agents/coordinate")
def omega_agents_coordinate(
    tasks: list[dict], omega: OmegaService = Depends(get_omega_service)
):
    return omega.coordinate_agents(tasks)


@app.post("/omega/agents/plan")
def omega_agents_plan(
    objective: str,
    available_agents: list[str],
    capabilities: dict | None = None,
    omega: OmegaService = Depends(get_omega_service),
):
    return omega.plan_tasks(objective, available_agents, capabilities or {})


@app.post("/omega/agents/consensus")
def omega_agents_consensus(
    proposal: dict,
    participants: list[str],
    omega: OmegaService = Depends(get_omega_service),
):
    return omega.consensus_propose(proposal, participants)


@app.post("/omega/agents/delegate")
def omega_agents_delegate(
    from_agent: str,
    to_agent: str,
    task: dict,
    omega: OmegaService = Depends(get_omega_service),
):
    return omega.delegate_task(from_agent, to_agent, task)


@app.post("/omega/distributed/sync")
def omega_distributed_sync(
    source_node: str,
    target_node: str,
    omega: OmegaService = Depends(get_omega_service),
):
    return omega._knowledge_sync.sync(source_node, target_node).to_dict()


# ---------------------------------------------------------------------------
# Agent Status & Knowledge Graph (Front-End Support)
# ---------------------------------------------------------------------------


@app.get("/agents")
def list_agents_with_status(
    container: ServiceContainer = Depends(get_container),
):
    agent_api = container.get("agent_api")
    if hasattr(agent_api, "list_agent_statuses"):
        return {"agents": agent_api.list_agent_statuses()}
    names = agent_api.list_agents()
    return {"agents": [{"name": n, "status": "idle", "updated_at": None} for n in names]}


@app.get("/knowledge/graph")
def knowledge_graph(
    db: Session = Depends(get_db),
    container: ServiceContainer = Depends(get_container),
):
    from knowledge.node import KnowledgeNode
    from knowledge.edge import KnowledgeEdge

    nodes = db.query(KnowledgeNode).order_by(KnowledgeNode.created_at.asc()).all()
    edges = db.query(KnowledgeEdge).order_by(KnowledgeEdge.created_at.asc()).all()
    return {
        "nodes": [
            {
                "id": n.id,
                "label": n.label,
                "type": n.node_type,
                "confidence": None,
            }
            for n in nodes
        ],
        "edges": [
            {
                "id": e.id,
                "source": e.subject_node_id,
                "target": e.object_node_id,
                "relation": e.predicate,
                "confidence": e.confidence,
            }
            for e in edges
        ],
    }


@app.get("/knowledge/timeline")
def knowledge_timeline(
    db: Session = Depends(get_db),
):
    from reasoning.models import KnowledgeFact
    from sqlalchemy import func
    facts = db.query(KnowledgeFact).order_by(KnowledgeFact.created_at.desc()).limit(100).all()
    return {
        "facts": [
            {
                "id": f.id,
                "subject": f.subject,
                "predicate": f.predicate,
                "object": f.object,
                "confidence": f.confidence,
                "created_at": f.created_at.isoformat(),
            }
            for f in facts
        ]
    }


# ---------------------------------------------------------------------------
# Simulation (Persistence)
# ---------------------------------------------------------------------------


import uuid
from core.database import SimulationRun


@app.post("/simulation/run")
def run_simulation(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    container: ServiceContainer = Depends(get_container),
):
    simulator = container.get("simulation_engine")
    device_id = payload.get("device_id", "")
    failure_mode = payload.get("failure_mode", "disconnect")
    if simulator is None:
        raise RuntimeError("SimulationEngine not registered")

    device_api = container.get("device_api")
    device_state = {}
    if device_api is not None:
        try:
            device_state = device_api.get(device_id) or {}
        except Exception:
            device_state = {}

    if failure_mode not in {"disconnect", "latency_spike", "write_failure"}:
        failure_mode = "disconnect"

    run_id = str(uuid.uuid4())
    sim_run = SimulationRun(
        id=run_id,
        device_id=device_id,
        failure_mode=failure_mode,
        status="running",
        progress="0%",
    )
    db.add(sim_run)
    db.commit()

    try:
        result = simulator.simulate(device_id, device_state, failure_mode)
        sim_run.status = "completed"
        sim_run.progress = "100%"
        sim_run.risk = result.get("risk", "unknown")
        sim_run.confidence = "high" if result.get("verification", {}).get("passed") else "low"
        sim_run.recovered = str(result.get("recovered", False)).lower()
        sim_run.impact = result.get("impact", "unknown")
        sim_run.result_json = json.dumps(result)
        sim_run.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {"run_id": run_id, **result}
    except Exception as e:
        sim_run.status = "failed"
        sim_run.result_json = json.dumps({"error": str(e)})
        db.commit()
        raise


@app.get("/simulation/list")
def list_simulations(db: Session = Depends(get_db)):
    runs = db.query(SimulationRun).order_by(SimulationRun.created_at.desc()).limit(50).all()
    return {
        "runs": [
            {
                "id": r.id,
                "device_id": r.device_id,
                "failure_mode": r.failure_mode,
                "status": r.status,
                "progress": r.progress,
                "risk": r.risk,
                "confidence": r.confidence,
                "recovered": r.recovered,
                "impact": r.impact,
                "result": json.loads(r.result_json) if r.result_json else {},
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in runs
        ]
    }


# ---------------------------------------------------------------------------
# Files Browser
# ---------------------------------------------------------------------------


import os as _os
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent / "workspace"
SEED_DIRS = [
    "Projects",
    "Research",
    "Models",
    "Agents",
    "Datasets",
    "Plugins",
    "Firmware",
    "Simulations",
    "Exports",
    "Recovery",
]


def _seed_workspace(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for d in SEED_DIRS:
        (root / d).mkdir(exist_ok=True)


_seed_workspace(WORKSPACE_ROOT)


def _safe_path(root: Path, rel_path: str) -> Path:
    if ".." in rel_path.split("/"):
        raise RuntimeError("Path traversal is not allowed")
    target = (root / rel_path).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise RuntimeError("Path traversal is not allowed")
    return target


def _list_dir(dir_path: Path) -> list[dict]:
    entries = []
    for p in sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
        try:
            stat = p.stat()
            entries.append(
                {
                    "name": p.name,
                    "type": "file" if p.is_file() else "directory",
                    "size": stat.st_size if p.is_file() else None,
                    "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                }
            )
        except PermissionError:
            continue
    return entries


@app.get("/files")
def list_files(path: str = ""):
    target = _safe_path(WORKSPACE_ROOT, path)
    if target.is_file():
        rel = target.relative_to(WORKSPACE_ROOT)
        return {"type": "file", "name": target.name, "path": str(rel), "size": target.stat().st_size}
    if target.is_dir():
        rel = target.relative_to(WORKSPACE_ROOT)
        return {"type": "directory", "path": str(rel) if rel != Path(".") else "", "entries": _list_dir(target)}
    return {"type": "directory", "path": "", "entries": _list_dir(WORKSPACE_ROOT)}


# ---------------------------------------------------------------------------
# Hardware HAL Snapshot
# ---------------------------------------------------------------------------


@app.get("/hardware")
def hardware_snapshot(
    epsilon: EpsilonService = Depends(get_epsilon_service),
    platform: PlatformService = Depends(get_platform_service),
):
    try:
        interfaces = epsilon.list_interfaces()
    except Exception:
        interfaces = {"interfaces": []}

    devices_platform = []
    try:
        devices_platform = platform.list_devices()
    except Exception:
        pass

    return {
        "hal": interfaces,
        "devices": devices_platform,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Assistant
# ---------------------------------------------------------------------------


@app.post("/assistant")
def assistant_query(
    payload: dict,
    db: Session = Depends(get_db),
    container: ServiceContainer = Depends(get_container),
):
    prompt = payload.get("prompt", "")
    if not prompt:
        raise RuntimeError("prompt is required")
    prompt_lower = prompt.lower().strip()
    platform = container.resolve("platform_service", PlatformService)

    if prompt_lower.startswith("dispatch "):
        parts = prompt_lower.split(" ", 2)
        agent_name = parts[1] if len(parts) > 1 else "echo"
        task = {"description": parts[2]} if len(parts) > 2 else {"description": "assistant task"}
        try:
            result = platform.dispatch_agent(db=db, agent_name=agent_name, task=task)
            return {"response": str(result)}
        except Exception as e:
            return {"response": f"Dispatch failed: {e}"}

    if prompt_lower == "help":
        return {
            "response": "Available commands: help, dispatch <agent> <task>, show devices, show agents, show kernel, status"
        }
    if prompt_lower == "show devices":
        return {"response": platform.list_devices()}
    if prompt_lower == "show agents":
        agent_api = container.get("agent_api")
        return {"response": agent_api.list_agents()}
    if prompt_lower == "show kernel":
        kernel = container.get("kernel")
        return {"response": kernel.status()}
    if prompt_lower == "status":
        return {"response": _status_snapshot(container, db)}

    return {"response": f"Processed: {prompt}"}


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


@app.get("/version")
def get_version():
    return {"version": config.version, "app": config.app_name}


# ---------------------------------------------------------------------------
# Phase Omega - Olympus (existing)
# ---------------------------------------------------------------------------


@app.get("/omega/dashboard/{section}")
def omega_dashboard_section(
    section: str, omega: OmegaService = Depends(get_omega_service)
):
    return omega.get_dashboard(section)
