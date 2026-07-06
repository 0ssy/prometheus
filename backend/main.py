"""
Prometheus Local API — Entry Point
-----------------------------------------
Run with: uvicorn backend.main:app --reload
(run from the prometheus/ root directory)

This wires up every Phase Alpha deliverable behind HTTP endpoints
so you can verify the whole loop by hand: start server, hit /health,
run a plugin, dispatch an agent, store/recall memory, query facts.
"""
import json

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from core.config import config
from core.logger import get_logger
from core.database import get_db
from core.bootstrap import boot
from core.ownership_registry import declare_owned, is_declared_owned, revoke_declaration, list_declared

from plugins.manager import plugin_manager

from agents.manager import agent_manager

from memory.store import remember, recall
from reasoning.graph import assert_fact, query_facts

from devices.registry import device_registry
from devices.simulated import SimulatedDevice
from devices.serial_device import SerialDevice
from engineering.partition_mapper import read_partition_table
from engineering.firmware_inspector import inspect_firmware
from engineering.boot_chain import analyze_boot_chain
from engineering.recovery_planner import plan_recovery
from engineering.device_simulator import SimulatedFirmwareDevice
from digital_twin.twin import build_twin

logger = get_logger(__name__)

app = FastAPI(title=config.app_name, version=config.version)


def _heartbeat_job():
    """Proves the scheduler runs without blocking the API."""
    logger.info("Prometheus heartbeat — system alive")


@app.on_event("startup")
def startup():
    boot(_heartbeat_job)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": config.app_name,
        "version": config.version,
        "plugins_loaded": plugin_manager.list_plugins(),
        "agents_loaded": agent_manager.list_agents(),
    }


@app.post("/plugins/{plugin_name}/run")
def run_plugin(plugin_name: str, payload: dict, db: Session = Depends(get_db)):
    context = {"db": db, "logger": logger}
    context.update(payload)
    result = plugin_manager.run(plugin_name, context)
    return result


@app.post("/agents/{agent_name}/dispatch")
def dispatch_agent(agent_name: str, task: dict, db: Session = Depends(get_db)):
    context = {"db": db, "logger": logger}
    result = agent_manager.dispatch(agent_name, task, context)
    return result


@app.post("/memory")
def store_memory(content: str, tag: str = "general", db: Session = Depends(get_db)):
    entry = remember(db, content=content, tag=tag, source="api")
    return {"id": entry.id, "content": entry.content, "tag": entry.tag}


@app.get("/memory")
def get_memory(tag: str | None = None, limit: int = 50, db: Session = Depends(get_db)):
    entries = recall(db, tag=tag, limit=limit)
    return [{"id": e.id, "content": e.content, "tag": e.tag, "created_at": str(e.created_at)} for e in entries]


@app.post("/knowledge")
def store_fact(subject: str, predicate: str, object: str, db: Session = Depends(get_db)):
    fact = assert_fact(db, subject, predicate, object)
    return {"id": fact.id, "subject": fact.subject, "predicate": fact.predicate, "object": fact.object}


@app.get("/knowledge")
def get_facts(subject: str | None = None, db: Session = Depends(get_db)):
    facts = query_facts(db, subject=subject)
    return [{"subject": f.subject, "predicate": f.predicate, "object": f.object} for f in facts]


# ---------------------------------------------------------------------------
# Phase Beta — Devices (RFC 0001)
# Every connect/disconnect/write is recorded as a knowledge-graph fact, per
# RFC 0001's design, using the exact same assert_fact() from Phase Alpha.
# ---------------------------------------------------------------------------

@app.post("/devices/simulated")
def register_simulated_device(
    device_id: str,
    latency_seconds: float = 0.0,
    failure_rate: float = 0.0,
    ownership_declared: bool = True,
    db: Session = Depends(get_db),
):
    device = SimulatedDevice(
        device_id=device_id,
        ownership_declared=ownership_declared,
        latency_seconds=latency_seconds,
        failure_rate=failure_rate,
    )
    device.connect()
    device_registry.register(device)
    assert_fact(db, subject=device_id, predicate="event", obj="connected")
    return {"device_id": device_id, "transport": "simulated", **device.status()}


@app.post("/devices/serial")
def register_serial_device(
    device_id: str,
    port: str,
    baudrate: int = 115200,
    ownership_declared: bool = False,
    db: Session = Depends(get_db),
):
    """
    ownership_declared defaults to False here deliberately (unlike the
    simulated endpoint) — a real device attaching to a real port is exactly
    the case RFC 0000 cares about. The caller must explicitly assert
    ownership; this is a "declared", not "verified", guarantee per RFC 0000.
    """
    device = SerialDevice(
        device_id=device_id, port=port, baudrate=baudrate, ownership_declared=ownership_declared
    )
    try:
        device.connect()
    except Exception as e:
        logger.exception(f"Failed to connect serial device {device_id}")
        assert_fact(db, subject=device_id, predicate="event", obj=f"connect_failed:{e}")
        raise
    device_registry.register(device)
    assert_fact(db, subject=device_id, predicate="event", obj="connected")
    return {"device_id": device_id, "transport": "serial", **device.status()}


@app.get("/devices")
def list_devices():
    return device_registry.list()


@app.get("/devices/{device_id}")
def get_device(device_id: str):
    device = device_registry.get(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail=f"No such device: {device_id}")
    return {"device_id": device.device_id, "transport": device.transport, **device.status()}


@app.post("/devices/{device_id}/write")
def write_device(device_id: str, payload: dict, db: Session = Depends(get_db)):
    device = device_registry.get(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail=f"No such device: {device_id}")
    value = payload.get("value")
    device.write(value)
    assert_fact(db, subject=device_id, predicate="wrote", obj=str(value))
    return {"device_id": device_id, "status": device.status()}


@app.post("/devices/{device_id}/disconnect")
def disconnect_device(device_id: str, db: Session = Depends(get_db)):
    device = device_registry.get(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail=f"No such device: {device_id}")
    device.disconnect()
    device_registry.unregister(device_id)
    assert_fact(db, subject=device_id, predicate="event", obj="disconnected")
    return {"device_id": device_id, "status": "disconnected"}


# ---------------------------------------------------------------------------
# Ownership (RFC 0000)
# Persistent out-of-band declarations — no bypassable query flags.
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
):
    parsed_recovery_policy = None
    if recovery_policy is not None:
        try:
            parsed_recovery_policy = json.loads(recovery_policy)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=422, detail=f"Invalid recovery_policy JSON: {e.msg}") from e
    entry = declare_owned(
        target_id,
        note=note,
        owner=owner,
        trust_level=trust_level,
        keys=keys,
        certificates=certificates,
        recovery_policy=parsed_recovery_policy,
    )
    assert_fact(db, subject=target_id, predicate="event", obj="ownership_declared")
    return entry


@app.get("/ownership")
def list_ownership():
    return list_declared()


@app.delete("/ownership/{target_id:path}")
def revoke_ownership(target_id: str, db: Session = Depends(get_db)):
    removed = revoke_declaration(target_id)
    if removed:
        assert_fact(db, subject=target_id, predicate="event", obj="ownership_revoked")
    return {"target_id": target_id, "revoked": removed}


# ---------------------------------------------------------------------------
# Phase Gamma — Partition Mapper (RFC 0002)
# Read-only. Requires persistent ownership declaration, not a URL flag.
# ---------------------------------------------------------------------------

@app.get("/gamma/partitions")
def get_partitions(disk_path: str, db: Session = Depends(get_db)):
    if not is_declared_owned(disk_path):
        raise HTTPException(
            status_code=403,
            detail=(
                f"{disk_path} is not in your declared-owned devices list. "
                f"Declare it first: POST /ownership/declare?target_id={disk_path}&note=..."
            ),
        )
    try:
        table = read_partition_table(disk_path, ownership_declared=True)
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail="OS denied access to this disk — on Windows, try running your terminal as Administrator.",
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No such disk path: {disk_path}")

    assert_fact(db, subject=disk_path, predicate="event", obj=f"partition_table_read:{table.scheme}")
    return table.to_dict()


@app.get("/gamma/firmware")
def get_firmware_report(path: str, db: Session = Depends(get_db)):
    if not is_declared_owned(path):
        raise HTTPException(
            status_code=403,
            detail=(
                f"{path} is not in your declared-owned devices list. "
                f"Declare it first: POST /ownership/declare?target_id={path}&note=..."
            ),
        )
    try:
        report = inspect_firmware(path, ownership_declared=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No such file: {path}")

    assert_fact(db, subject=path, predicate="event", obj=f"firmware_inspected:{report.format}")
    return report.to_dict()


@app.get("/gamma/simulate/{scenario}")
def run_gamma_simulation(scenario: str, db: Session = Depends(get_db)):
    """
    Runs the full Boot Chain Analyzer + Recovery Planner pipeline against
    a SimulatedFirmwareDevice — no hardware required. scenario is "valid"
    or "tampered".
    """
    if scenario not in ("valid", "tampered"):
        raise HTTPException(status_code=400, detail="scenario must be 'valid' or 'tampered'")

    device = SimulatedFirmwareDevice(f"sim_{scenario}", tampered=(scenario == "tampered"))
    boot_result = analyze_boot_chain(device.firmware_bytes, device.signature, device.public_key_bytes)
    plan = plan_recovery(device.device_id, boot_chain_status=boot_result.status, partition_scheme="gpt")

    assert_fact(db, subject=device.device_id, predicate="event", obj=f"boot_chain:{boot_result.status}")

    return {
        "device_id": device.device_id,
        "boot_chain_result": boot_result.to_dict(),
        "recovery_plan": plan.to_dict(),
    }


# ---------------------------------------------------------------------------
# Phase Delta — Digital Twin Engine (RFC 0003)
# Materialized view over the knowledge graph. READ-ONLY.
# ---------------------------------------------------------------------------

@app.get("/delta/twin/{device_id}")
def get_device_twin(device_id: str, db: Session = Depends(get_db)):
    twin = build_twin(db, device_id)
    return twin.to_dict()
