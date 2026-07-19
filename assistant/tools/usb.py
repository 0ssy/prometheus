"""Assistant tools for the USB capability.

Each tool is described using the SDK's `PluginCapability` shape so the
Assistant (and any plugin host) can discover the USB capability, see its
required permissions, and invoke it. Tools delegate to the USB Hardware
API and the automation action registry.
"""

from __future__ import annotations

from typing import Any

from sdk.plugin_sdk import PluginCapability, PluginResult

from hardware.usb import UsbCapability, get_usb_manager
from automation.actions import usb_actions


def tool_enumerate(_payload: dict[str, Any]) -> PluginResult:
    manager = get_usb_manager()
    devices = manager.enumerate()
    return PluginResult.ok(
        {
            "count": len(devices),
            "devices": [d.to_dict() for d in devices],
        }
    )


def tool_info(payload: dict[str, Any]) -> PluginResult:
    device_id = payload.get("device_id")
    if not device_id:
        return PluginResult.fail("missing 'device_id'")
    dev = get_usb_manager().get(device_id)
    if dev is None:
        return PluginResult.fail(f"unknown device: {device_id}")
    return PluginResult.ok(dev.to_dict())


def tool_allow(payload: dict[str, Any]) -> PluginResult:
    result = usb_actions.usb_allow(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_deny(payload: dict[str, Any]) -> PluginResult:
    result = usb_actions.usb_deny(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


USB_TOOLS: list[PluginCapability] = [
    PluginCapability(
        name="usb.enumerate",
        description="List all currently attached USB devices with vendor/product ids and metadata.",
        permissions={"device.status"},
        executor=tool_enumerate,
    ),
    PluginCapability(
        name="usb.info",
        description="Get detailed information about a specific USB device by device_id.",
        permissions={"device.status"},
        executor=tool_info,
    ),
    PluginCapability(
        name="usb.allow",
        description=(
            "Grant access to a USB device (by vendor_id/product_id/serial) for the "
            "given capabilities."
        ),
        permissions={"device.connect"},
        executor=tool_allow,
    ),
    PluginCapability(
        name="usb.deny",
        description="Deny access to a USB device (by vendor_id/product_id/serial).",
        permissions={"device.connect"},
        executor=tool_deny,
    ),
]


def invoke(tool_name: str, payload: dict[str, Any]) -> PluginResult:
    for tool in USB_TOOLS:
        if tool.name == tool_name and tool.executor is not None:
            return tool.executor(payload)
    return PluginResult.fail(f"unknown usb tool: {tool_name}")
