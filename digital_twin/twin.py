"""
Prometheus Digital Twin Engine (RFC 0003)
-----------------------------------------
Builds a DeviceTwin — the nine-field model from the original plan —
purely by aggregating facts Beta and Gamma already wrote to the
knowledge graph. This is a materialized VIEW, not a second source of
truth.

History is naturally append-only since assert_fact() never updates
or deletes rows.

Health is a simple rules-based score (0.0-1.0) for v0.1 — no ML,
per RFC 0003's explicit non-goal.
"""

from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session

from reasoning.graph import query_facts
from contracts.device import DeviceApi
from devices.registry import device_registry
from core.ownership_registry import is_declared_owned
from engineering.recovery_planner import plan_recovery
from core.logger import get_logger

logger = get_logger(__name__)

CONNECTION_EVENTS = ("connected", "disconnected")


@dataclass
class DeviceTwin:
    device_id: str
    identity: dict
    firmware: dict
    hardware: dict
    sensors: dict
    state: str
    logs: list
    health: float
    recovery_options: list
    history: list

    def to_dict(self) -> dict:
        return asdict(self)


def _derive_state(events: list[str]) -> str:
    """
    Only looks at connection-specific events (connected/disconnected/
    connect_failed) — not every event written for this subject. Without
    this filter, an unrelated later event (e.g. partition_table_read)
    would incorrectly overwrite a perfectly good "online" signal.
    """
    connection_events = [
        e for e in events if e in CONNECTION_EVENTS or e.startswith("connect_failed")
    ]
    if not connection_events:
        return "unknown"
    last = connection_events[-1]
    if last.startswith("connect_failed"):
        return "degraded"
    if last == "connected":
        return "online"
    if last == "disconnected":
        return "offline"
    return "unknown"


def _derive_health(facts_by_predicate: dict) -> float:
    score = 1.0
    events = facts_by_predicate.get("event", [])

    if any(e.startswith("connect_failed") for e in events):
        score -= 0.5
    if any(e == "boot_chain:invalid" for e in events):
        score -= 0.4
    if any(e == "boot_chain:unknown" for e in events):
        score -= 0.1
    if _derive_state(events) == "offline":
        score -= 0.2

    return max(0.0, min(1.0, score))


def build_twin(db: Session, device_id: str, device_api: DeviceApi | None = None) -> DeviceTwin:
    facts = query_facts(db, subject=device_id)
    facts_sorted = sorted(facts, key=lambda f: f.created_at)

    facts_by_predicate: dict[str, list[str]] = {}
    history = []
    for f in facts_sorted:
        facts_by_predicate.setdefault(f.predicate, []).append(f.object)
        history.append(
            {
                "timestamp": f.created_at.isoformat(),
                "predicate": f.predicate,
                "object": f.object,
            }
        )

    events = facts_by_predicate.get("event", [])
    state = _derive_state(events)
    health = _derive_health(facts_by_predicate)

    firmware = {}
    firmware_events = [e for e in events if e.startswith("firmware_inspected:")]
    if firmware_events:
        firmware["format"] = firmware_events[-1].split(":", 1)[1]

    boot_chain_events = [e for e in events if e.startswith("boot_chain:")]
    boot_chain_status = (
        boot_chain_events[-1].split(":", 1)[1] if boot_chain_events else "unknown"
    )
    if boot_chain_events:
        firmware["boot_chain_status"] = boot_chain_status

    partition_events = [e for e in events if e.startswith("partition_table_read:")]
    partition_scheme = (
        partition_events[-1].split(":", 1)[1] if partition_events else "unknown"
    )

    registry = device_api or device_registry
    live_device = registry.get(device_id)
    if live_device:
        hardware = {"transport": live_device.transport, **live_device.status()}
    else:
        hardware = {
            "transport": "unknown",
            "note": "not currently registered — historical facts only",
        }

    sensors = {}
    wrote_events = facts_by_predicate.get("wrote", [])
    if wrote_events:
        sensors["last_value"] = wrote_events[-1]

    identity = {
        "device_id": device_id,
        "ownership_declared": is_declared_owned(device_id),
    }

    logs = [
        f"See core/logger.py output for {device_id} — {len(facts_sorted)} knowledge-graph event(s) recorded"
    ]

    recovery_options = []
    if boot_chain_events or partition_events:
        plan = plan_recovery(
            device_id,
            boot_chain_status=boot_chain_status,
            partition_scheme=partition_scheme,
        )
        recovery_options = plan.to_dict()["steps"]

    twin = DeviceTwin(
        device_id=device_id,
        identity=identity,
        firmware=firmware,
        hardware=hardware,
        sensors=sensors,
        state=state,
        logs=logs,
        health=health,
        recovery_options=recovery_options,
        history=history,
    )
    logger.info(
        f"Built twin for {device_id}: state={state}, health={health}, {len(history)} history entries"
    )
    return twin
