"""Serial communication automation actions.

Implements the `serial:*` automation actions consumed by the workflow engine.
Each action operates on the Serial Hardware API and returns a JSON-serializable
result.
"""

from __future__ import annotations

from typing import Any, Callable

from hardware.serial import SerialCapability, get_serial_manager


def serial_enumerate(_params: dict[str, Any]) -> dict[str, Any]:
    manager = get_serial_manager()
    ports = manager.enumerate()
    return {"count": len(ports), "ports": [p.to_dict() for p in ports]}


def serial_info(params: dict[str, Any]) -> dict[str, Any]:
    manager = get_serial_manager()
    port = params.get("port")
    if not port:
        return {"error": "missing port"}
    sp = manager.get(port)
    if sp is None:
        return {"error": f"unknown port: {port}"}
    return sp.to_dict()


def serial_connect(params: dict[str, Any]) -> dict[str, Any]:
    manager = get_serial_manager()
    port = params.get("port")
    baud = int(params.get("baud_rate", 115200))
    if not port:
        return {"error": "missing port"}
    return manager.connect(port, baud_rate=baud)


def serial_disconnect(params: dict[str, Any]) -> dict[str, Any]:
    manager = get_serial_manager()
    port = params.get("port")
    if not port:
        return {"error": "missing port"}
    return manager.disconnect(port)


def serial_allow(params: dict[str, Any]) -> dict[str, Any]:
    manager = get_serial_manager()
    caps = params.get("capabilities")
    manager.policy().allow(
        port=params.get("port"),
        vendor_id=int(params["vendor_id"], 0) if isinstance(params.get("vendor_id"), str) else params.get("vendor_id"),
        product_id=int(params["product_id"], 0) if isinstance(params.get("product_id"), str) else params.get("product_id"),
        serial=params.get("serial"),
        capabilities=frozenset(SerialCapability(c) for c in caps) if caps else None,
    )
    return {"status": "allowed", "port": params.get("port")}


def serial_deny(params: dict[str, Any]) -> dict[str, Any]:
    manager = get_serial_manager()
    manager.policy().deny(
        port=params.get("port"),
        vendor_id=int(params["vendor_id"], 0) if isinstance(params.get("vendor_id"), str) else params.get("vendor_id"),
        product_id=int(params["product_id"], 0) if isinstance(params.get("product_id"), str) else params.get("product_id"),
        serial=params.get("serial"),
        reason=params.get("reason", "denied by policy"),
    )
    return {"status": "denied", "port": params.get("port")}


SERIAL_ACTIONS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "serial:enumerate": serial_enumerate,
    "serial:info": serial_info,
    "serial:connect": serial_connect,
    "serial:disconnect": serial_disconnect,
    "serial:allow": serial_allow,
    "serial:deny": serial_deny,
}


def run_serial_action(action: str, params: dict[str, Any]) -> dict[str, Any]:
    handler = SERIAL_ACTIONS.get(action)
    if handler is None:
        return {"error": f"unknown serial action: {action}"}
    return handler(params)
