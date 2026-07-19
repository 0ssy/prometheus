"""Fastboot automation actions.

Implements the `fastboot:*` automation actions consumed by the workflow
engine. Each action operates on the Fastboot Hardware API and returns a
JSON-serializable result.
"""

from __future__ import annotations

from typing import Any, Callable

from hardware.fastboot import FastbootCapability, get_fastboot_manager


def _known(serial: str | None) -> str | None:
    if not serial:
        return None
    return serial if get_fastboot_manager().get(serial) is not None else None


def fastboot_enumerate(_params: dict[str, Any]) -> dict[str, Any]:
    manager = get_fastboot_manager()
    devices = manager.enumerate()
    return {"count": len(devices), "devices": [d.to_dict() for d in devices]}


def fastboot_getvar(params: dict[str, Any]) -> dict[str, Any]:
    serial = params.get("serial")
    if not serial:
        return {"error": "missing serial"}
    if _known(serial) is None:
        return {"error": f"unknown device: {serial}"}
    return get_fastboot_manager().getvar(serial, variable=params.get("variable", "all"))


def fastboot_unlock(params: dict[str, Any]) -> dict[str, Any]:
    serial = params.get("serial")
    if not serial:
        return {"error": "missing serial"}
    if _known(serial) is None:
        return {"error": f"unknown device: {serial}"}
    return get_fastboot_manager().unlock(serial)


def fastboot_lock(params: dict[str, Any]) -> dict[str, Any]:
    serial = params.get("serial")
    if not serial:
        return {"error": "missing serial"}
    if _known(serial) is None:
        return {"error": f"unknown device: {serial}"}
    return get_fastboot_manager().lock(serial)


def fastboot_flash(params: dict[str, Any]) -> dict[str, Any]:
    serial = params.get("serial")
    partition = params.get("partition")
    image = params.get("image")
    if not serial or not partition or not image:
        return {"error": "missing serial/partition/image"}
    if _known(serial) is None:
        return {"error": f"unknown device: {serial}"}
    return get_fastboot_manager().flash(serial, partition, image)


def fastboot_erase(params: dict[str, Any]) -> dict[str, Any]:
    serial = params.get("serial")
    partition = params.get("partition")
    if not serial or not partition:
        return {"error": "missing serial/partition"}
    if _known(serial) is None:
        return {"error": f"unknown device: {serial}"}
    return get_fastboot_manager().erase(serial, partition)


def fastboot_boot(params: dict[str, Any]) -> dict[str, Any]:
    serial = params.get("serial")
    image = params.get("image")
    if not serial or not image:
        return {"error": "missing serial/image"}
    if _known(serial) is None:
        return {"error": f"unknown device: {serial}"}
    return get_fastboot_manager().boot(serial, image)


def fastboot_reboot(params: dict[str, Any]) -> dict[str, Any]:
    serial = params.get("serial")
    if not serial:
        return {"error": "missing serial"}
    if _known(serial) is None:
        return {"error": f"unknown device: {serial}"}
    return get_fastboot_manager().reboot(serial, mode=params.get("mode", "normal"))


def fastboot_allow(params: dict[str, Any]) -> dict[str, Any]:
    manager = get_fastboot_manager()
    caps = params.get("capabilities")
    manager.policy().allow(
        serial=params.get("serial"),
        vendor_id=int(params["vendor_id"], 0) if isinstance(params.get("vendor_id"), str) else params.get("vendor_id"),
        product_id=int(params["product_id"], 0) if isinstance(params.get("product_id"), str) else params.get("product_id"),
        capabilities=frozenset(FastbootCapability(c) for c in caps) if caps else None,
    )
    return {"status": "allowed", "serial": params.get("serial")}


def fastboot_deny(params: dict[str, Any]) -> dict[str, Any]:
    manager = get_fastboot_manager()
    manager.policy().deny(
        serial=params.get("serial"),
        vendor_id=int(params["vendor_id"], 0) if isinstance(params.get("vendor_id"), str) else params.get("vendor_id"),
        product_id=int(params["product_id"], 0) if isinstance(params.get("product_id"), str) else params.get("product_id"),
        reason=params.get("reason", "denied by policy"),
    )
    return {"status": "denied", "serial": params.get("serial")}


FASTBOOT_ACTIONS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "fastboot:enumerate": fastboot_enumerate,
    "fastboot:getvar": fastboot_getvar,
    "fastboot:unlock": fastboot_unlock,
    "fastboot:lock": fastboot_lock,
    "fastboot:flash": fastboot_flash,
    "fastboot:erase": fastboot_erase,
    "fastboot:boot": fastboot_boot,
    "fastboot:reboot": fastboot_reboot,
    "fastboot:allow": fastboot_allow,
    "fastboot:deny": fastboot_deny,
}


def run_fastboot_action(action: str, params: dict[str, Any]) -> dict[str, Any]:
    handler = FASTBOOT_ACTIONS.get(action)
    if handler is None:
        return {"error": f"unknown fastboot action: {action}"}
    return handler(params)
