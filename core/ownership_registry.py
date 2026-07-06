"""
Persistent Ownership Declarations (RFC 0000)
-----------------------------------------
Upgrade from a per-request ownership_declared=True query flag: ownership
must now be declared once, out-of-band, before any Gamma module will
touch a target. Still an honor system — RFC 0000 is explicit that this
is "declared", not "verified" — but it closes the gap of "anyone can
just type ?ownership_declared=true in a URL."
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from core.logger import get_logger

logger = get_logger(__name__)

OWNED_DEVICES_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "owned_devices.json"
)


def _load() -> dict:
    if not OWNED_DEVICES_PATH.exists():
        return {"declared_owners": []}
    with open(OWNED_DEVICES_PATH, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    OWNED_DEVICES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OWNED_DEVICES_PATH, "w") as f:
        json.dump(data, f, indent=2)


def is_declared_owned(target_id: str) -> bool:
    data = _load()
    return any(entry["id"] == target_id for entry in data.get("declared_owners", []))


def declare_owned(
    target_id: str,
    note: str = "",
    owner: str = "",
    trust_level: str = "declared",
    keys: list | None = None,
    certificates: list | None = None,
    recovery_policy: dict | None = None,
) -> dict:
    data = _load()
    if is_declared_owned(target_id):
        logger.info(f"{target_id} already declared owned — no change")
        return {"id": target_id, "already_declared": True}
    entry = {
        "id": target_id,
        "owner": owner,
        "declared_at": datetime.now(timezone.utc).isoformat(),
        "note": note,
        "trust_level": trust_level,
        "keys": keys or [],
        "certificates": certificates or [],
        "recovery_policy": recovery_policy,
    }
    data.setdefault("declared_owners", []).append(entry)
    _save(data)
    logger.info(
        f"Declared ownership: {target_id} (owner={owner!r}, trust_level={trust_level})"
    )
    return entry


def revoke_declaration(target_id: str) -> bool:
    data = _load()
    before = len(data.get("declared_owners", []))
    data["declared_owners"] = [
        e for e in data.get("declared_owners", []) if e["id"] != target_id
    ]
    _save(data)
    removed = before != len(data["declared_owners"])
    if removed:
        logger.info(f"Revoked ownership declaration: {target_id}")
    return removed


def list_declared() -> list:
    return _load().get("declared_owners", [])
