"""ADB (Android Debug Bridge) automation actions.

Implements the `adb:*` automation actions consumed by the workflow engine.
Each action operates on the ADB Hardware API and returns a JSON-serializable
result.
"""

from __future__ import annotations

from typing import Any, Callable

from hardware.adb import AdbCapability, get_adb_manager


def _known(serial: str | None) -> str | None:
    if not serial:
        return None
    return serial if get_adb_manager().get(serial) is not None else None


def adb_enumerate(_params: dict[str, Any]) -> dict[str, Any]:
    manager = get_adb_manager()
    devices = manager.enumerate()
    return {"count": len(devices), "devices": [d.to_dict() for d in devices]}


def adb_shell(params: dict[str, Any]) -> dict[str, Any]:
    serial = params.get("serial")
    command = params.get("command")
    if not serial or command is None:
        return {"error": "missing serial or command"}
    if _known(serial) is None:
        return {"error": f"unknown device: {serial}"}
    return get_adb_manager().shell(serial, command)


def adb_logcat(params: dict[str, Any]) -> dict[str, Any]:
    serial = params.get("serial")
    if not serial:
        return {"error": "missing serial"}
    if _known(serial) is None:
        return {"error": f"unknown device: {serial}"}
    return get_adb_manager().logcat(serial, lines=int(params.get("lines", 100)))


def adb_push(params: dict[str, Any]) -> dict[str, Any]:
    serial = params.get("serial")
    if not serial or "local" not in params or "remote" not in params:
        return {"error": "missing serial/local/remote"}
    if _known(serial) is None:
        return {"error": f"unknown device: {serial}"}
    return get_adb_manager().push(serial, params["local"], params["remote"])


def adb_pull(params: dict[str, Any]) -> dict[str, Any]:
    serial = params.get("serial")
    if not serial or "remote" not in params or "local" not in params:
        return {"error": "missing serial/remote/local"}
    if _known(serial) is None:
        return {"error": f"unknown device: {serial}"}
    return get_adb_manager().pull(serial, params["remote"], params["local"])


def adb_install(params: dict[str, Any]) -> dict[str, Any]:
    serial = params.get("serial")
    apk = params.get("apk")
    if not serial or not apk:
        return {"error": "missing serial or apk"}
    if _known(serial) is None:
        return {"error": f"unknown device: {serial}"}
    return get_adb_manager().install(serial, apk)


def adb_reboot(params: dict[str, Any]) -> dict[str, Any]:
    serial = params.get("serial")
    if not serial:
        return {"error": "missing serial"}
    if _known(serial) is None:
        return {"error": f"unknown device: {serial}"}
    return get_adb_manager().reboot(serial, mode=params.get("mode", "normal"))


def adb_sideload(params: dict[str, Any]) -> dict[str, Any]:
    serial = params.get("serial")
    ota = params.get("ota")
    if not serial or not ota:
        return {"error": "missing serial or ota"}
    if _known(serial) is None:
        return {"error": f"unknown device: {serial}"}
    return get_adb_manager().sideload(serial, ota)


def adb_allow(params: dict[str, Any]) -> dict[str, Any]:
    manager = get_adb_manager()
    caps = params.get("capabilities")
    manager.policy().allow(
        serial=params.get("serial"),
        vendor_id=int(params["vendor_id"], 0) if isinstance(params.get("vendor_id"), str) else params.get("vendor_id"),
        product_id=int(params["product_id"], 0) if isinstance(params.get("product_id"), str) else params.get("product_id"),
        capabilities=frozenset(AdbCapability(c) for c in caps) if caps else None,
    )
    return {"status": "allowed", "serial": params.get("serial")}


def adb_deny(params: dict[str, Any]) -> dict[str, Any]:
    manager = get_adb_manager()
    manager.policy().deny(
        serial=params.get("serial"),
        vendor_id=int(params["vendor_id"], 0) if isinstance(params.get("vendor_id"), str) else params.get("vendor_id"),
        product_id=int(params["product_id"], 0) if isinstance(params.get("product_id"), str) else params.get("product_id"),
        reason=params.get("reason", "denied by policy"),
    )
    return {"status": "denied", "serial": params.get("serial")}


ADB_ACTIONS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "adb:enumerate": adb_enumerate,
    "adb:shell": adb_shell,
    "adb:logcat": adb_logcat,
    "adb:push": adb_push,
    "adb:pull": adb_pull,
    "adb:install": adb_install,
    "adb:reboot": adb_reboot,
    "adb:sideload": adb_sideload,
    "adb:allow": adb_allow,
    "adb:deny": adb_deny,
}


def run_adb_action(action: str, params: dict[str, Any]) -> dict[str, Any]:
    handler = ADB_ACTIONS.get(action)
    if handler is None:
        return {"error": f"unknown adb action: {action}"}
    return handler(params)
