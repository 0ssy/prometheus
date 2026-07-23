"""Assistant tools for the ADB (Android Debug Bridge) capability.

Each tool is described using the SDK's `PluginCapability` shape so the
Assistant (and any plugin host) can discover the ADB capability, see its
required permissions, and invoke it. Tools delegate to the ADB Hardware API
and the automation action registry.
"""

from __future__ import annotations

from typing import Any

from sdk.plugin_sdk import PluginCapability, PluginResult

from hardware.adb import get_adb_manager
from automation.actions import adb_actions


def tool_enumerate(_payload: dict[str, Any]) -> PluginResult:
    manager = get_adb_manager()
    devices = manager.enumerate()
    return PluginResult.ok({"count": len(devices), "devices": [d.to_dict() for d in devices]})


def tool_shell(payload: dict[str, Any]) -> PluginResult:
    result = adb_actions.adb_shell(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_logcat(payload: dict[str, Any]) -> PluginResult:
    result = adb_actions.adb_logcat(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_push(payload: dict[str, Any]) -> PluginResult:
    result = adb_actions.adb_push(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_pull(payload: dict[str, Any]) -> PluginResult:
    result = adb_actions.adb_pull(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_install(payload: dict[str, Any]) -> PluginResult:
    result = adb_actions.adb_install(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_reboot(payload: dict[str, Any]) -> PluginResult:
    result = adb_actions.adb_reboot(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_sideload(payload: dict[str, Any]) -> PluginResult:
    result = adb_actions.adb_sideload(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_allow(payload: dict[str, Any]) -> PluginResult:
    result = adb_actions.adb_allow(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_deny(payload: dict[str, Any]) -> PluginResult:
    result = adb_actions.adb_deny(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


ADB_TOOLS: list[PluginCapability] = [
    PluginCapability(
        name="adb.enumerate",
        description="List all connected Android (ADB) devices with metadata.",
        permissions={"device.status"},
        executor=tool_enumerate,
    ),
    PluginCapability(
        name="adb.shell",
        description="Run a shell command on an Android device.",
        permissions={"device.connect"},
        executor=tool_shell,
    ),
    PluginCapability(
        name="adb.logcat",
        description="Capture logcat output from an Android device.",
        permissions={"device.connect"},
        executor=tool_logcat,
    ),
    PluginCapability(
        name="adb.push",
        description="Push a local file to an Android device.",
        permissions={"device.write"},
        executor=tool_push,
    ),
    PluginCapability(
        name="adb.pull",
        description="Pull a file from an Android device to local storage.",
        permissions={"device.read"},
        executor=tool_pull,
    ),
    PluginCapability(
        name="adb.install",
        description="Install an APK on an Android device.",
        permissions={"device.write"},
        executor=tool_install,
    ),
    PluginCapability(
        name="adb.reboot",
        description="Reboot an Android device (normal/recovery/bootloader).",
        permissions={"device.reboot"},
        executor=tool_reboot,
    ),
    PluginCapability(
        name="adb.sideload",
        description="Sideload an OTA package to a device in recovery.",
        permissions={"device.write"},
        executor=tool_sideload,
    ),
    PluginCapability(
        name="adb.allow",
        description="Grant access to an Android device for the given capabilities.",
        permissions={"device.connect"},
        executor=tool_allow,
    ),
    PluginCapability(
        name="adb.deny",
        description="Deny access to an Android device.",
        permissions={"device.connect"},
        executor=tool_deny,
    ),
]


def invoke(tool_name: str, payload: dict[str, Any]) -> PluginResult:
    for tool in ADB_TOOLS:
        if tool.name == tool_name and tool.executor is not None:
            return tool.executor(payload)
    return PluginResult.fail(f"unknown adb tool: {tool_name}")
