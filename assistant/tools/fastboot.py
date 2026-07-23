"""Assistant tools for the Fastboot capability.

Each tool is described using the SDK's `PluginCapability` shape so the
Assistant (and any plugin host) can discover the Fastboot capability, see its
required permissions, and invoke it. Tools delegate to the Fastboot Hardware
API and the automation action registry.
"""

from __future__ import annotations

from typing import Any

from sdk.plugin_sdk import PluginCapability, PluginResult

from hardware.fastboot import get_fastboot_manager
from automation.actions import fastboot_actions


def tool_enumerate(_payload: dict[str, Any]) -> PluginResult:
    manager = get_fastboot_manager()
    devices = manager.enumerate()
    return PluginResult.ok({"count": len(devices), "devices": [d.to_dict() for d in devices]})


def tool_getvar(payload: dict[str, Any]) -> PluginResult:
    result = fastboot_actions.fastboot_getvar(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_unlock(payload: dict[str, Any]) -> PluginResult:
    result = fastboot_actions.fastboot_unlock(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_lock(payload: dict[str, Any]) -> PluginResult:
    result = fastboot_actions.fastboot_lock(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_flash(payload: dict[str, Any]) -> PluginResult:
    result = fastboot_actions.fastboot_flash(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_erase(payload: dict[str, Any]) -> PluginResult:
    result = fastboot_actions.fastboot_erase(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_boot(payload: dict[str, Any]) -> PluginResult:
    result = fastboot_actions.fastboot_boot(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_reboot(payload: dict[str, Any]) -> PluginResult:
    result = fastboot_actions.fastboot_reboot(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_allow(payload: dict[str, Any]) -> PluginResult:
    result = fastboot_actions.fastboot_allow(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_deny(payload: dict[str, Any]) -> PluginResult:
    result = fastboot_actions.fastboot_deny(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


FASTBOOT_TOOLS: list[PluginCapability] = [
    PluginCapability(
        name="fastboot.enumerate",
        description="List all devices in fastboot mode with metadata.",
        permissions={"device.status"},
        executor=tool_enumerate,
    ),
    PluginCapability(
        name="fastboot.getvar",
        description="Read a bootloader variable from a device.",
        permissions={"device.status"},
        executor=tool_getvar,
    ),
    PluginCapability(
        name="fastboot.unlock",
        description="Unlock the bootloader (destructive — permits flashing).",
        permissions={"device.flash"},
        executor=tool_unlock,
    ),
    PluginCapability(
        name="fastboot.lock",
        description="Lock the bootloader.",
        permissions={"device.flash"},
        executor=tool_lock,
    ),
    PluginCapability(
        name="fastboot.flash",
        description="Flash an image to a partition.",
        permissions={"device.flash"},
        executor=tool_flash,
    ),
    PluginCapability(
        name="fastboot.erase",
        description="Erase a partition.",
        permissions={"device.flash"},
        executor=tool_erase,
    ),
    PluginCapability(
        name="fastboot.boot",
        description="Boot an image without flashing it.",
        permissions={"device.flash"},
        executor=tool_boot,
    ),
    PluginCapability(
        name="fastboot.reboot",
        description="Reboot a device from fastboot mode.",
        permissions={"device.reboot"},
        executor=tool_reboot,
    ),
    PluginCapability(
        name="fastboot.allow",
        description="Grant access to a fastboot device for the given capabilities.",
        permissions={"device.connect"},
        executor=tool_allow,
    ),
    PluginCapability(
        name="fastboot.deny",
        description="Deny access to a fastboot device.",
        permissions={"device.connect"},
        executor=tool_deny,
    ),
]


def invoke(tool_name: str, payload: dict[str, Any]) -> PluginResult:
    for tool in FASTBOOT_TOOLS:
        if tool.name == tool_name and tool.executor is not None:
            return tool.executor(payload)
    return PluginResult.fail(f"unknown fastboot tool: {tool_name}")
