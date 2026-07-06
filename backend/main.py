"""
Prometheus Local API — Entry Point
-----------------------------------------
Run with: uvicorn backend.main:app --reload
(run from the prometheus/ root directory)

All subsystems are wired through the ServiceContainer bootstrapped
at startup. Endpoints access services via the container rather than
direct imports.
"""

import json

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from core.config import config
from core.logger import get_logger
from core.database import get_db
from core.bootstrap import boot
from core.container import ServiceContainer
from services.platform_service import PlatformService
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


@app.on_event("startup")
def startup():
    global _container
    _container = boot(_heartbeat_job)
    logger.info("Backend ready — services available via app.state.container")


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
        raise RuntimeError(
            f"{disk_path} is not in your declared-owned devices list. "
            f"Declare it first: POST /ownership/declare?target_id={disk_path}&note=..."
        )
    try:
        from engineering.partition_mapper import read_partition_table

        table = read_partition_table(disk_path, ownership_declared=True)
    except PermissionError:
        raise RuntimeError(
            "OS denied access to this disk — on Windows, try running your terminal as Administrator."
        )
    except FileNotFoundError:
        raise RuntimeError(f"No such disk path: {disk_path}")

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
        raise RuntimeError(
            f"{path} is not in your declared-owned devices list. "
            f"Declare it first: POST /ownership/declare?target_id={path}&note=..."
        )
    try:
        from engineering.firmware_inspector import inspect_firmware

        report = inspect_firmware(path, ownership_declared=True)
    except FileNotFoundError:
        raise RuntimeError(f"No such file: {path}")

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
