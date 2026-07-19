"""USB automation actions.

Implements the `usb:*` automation actions consumed by the workflow engine
and any other automation dispatcher. Each action is a pure function that
operates on the USB Hardware API and returns a JSON-serializable result.
"""

from __future__ import annotations

from typing import Any, Callable

from hardware.usb import UsbCapability, get_usb_manager


def usb_enumerate(_params: dict[str, Any]) -> dict[str, Any]:
    manager = get_usb_manager()
    devices = manager.enumerate()
    return {"count": len(devices), "devices": [d.to_dict() for d in devices]}


def usb_info(params: dict[str, Any]) -> dict[str, Any]:
    manager = get_usb_manager()
    device_id = params.get("device_id")
    if not device_id:
        return {"error": "missing device_id"}
    dev = manager.get(device_id)
    if dev is None:
        return {"error": f"unknown device: {device_id}"}
    return dev.to_dict()


def usb_allow(params: dict[str, Any]) -> dict[str, Any]:
    manager = get_usb_manager()
    vid = params.get("vendor_id")
    pid = params.get("product_id")
    serial = params.get("serial")
    caps = params.get("capabilities")
    manager.policy().allow(
        vendor_id=int(vid, 0) if isinstance(vid, str) else vid,
        product_id=int(pid, 0) if isinstance(pid, str) else pid,
        serial=serial,
        capabilities=frozenset(UsbCapability(c) for c in caps) if caps else None,
    )
    return {"status": "allowed", "vendor_id": vid, "product_id": pid, "serial": serial}


def usb_deny(params: dict[str, Any]) -> dict[str, Any]:
    manager = get_usb_manager()
    vid = params.get("vendor_id")
    pid = params.get("product_id")
    serial = params.get("serial")
    reason = params.get("reason", "denied by policy")
    manager.policy().deny(
        vendor_id=int(vid, 0) if isinstance(vid, str) else vid,
        product_id=int(pid, 0) if isinstance(pid, str) else pid,
        serial=serial,
        reason=reason,
    )
    return {"status": "denied", "vendor_id": vid, "product_id": pid, "serial": serial}


# Action registry: name -> handler.
USB_ACTIONS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "usb:enumerate": usb_enumerate,
    "usb:info": usb_info,
    "usb:allow": usb_allow,
    "usb:deny": usb_deny,
}


def run_usb_action(action: str, params: dict[str, Any]) -> dict[str, Any]:
    handler = USB_ACTIONS.get(action)
    if handler is None:
        return {"error": f"unknown usb action: {action}"}
    return handler(params)
