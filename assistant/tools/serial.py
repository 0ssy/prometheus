"""Assistant tools for the Serial communication capability.

Each tool is described using the SDK's `PluginCapability` shape so the
Assistant (and any plugin host) can discover the Serial capability, see its
required permissions, and invoke it. Tools delegate to the Serial Hardware
API and the automation action registry.
"""

from __future__ import annotations

from typing import Any

from sdk.plugin_sdk import PluginCapability, PluginResult

from hardware.serial import get_serial_manager
from automation.actions import serial_actions


def tool_enumerate(_payload: dict[str, Any]) -> PluginResult:
    manager = get_serial_manager()
    ports = manager.enumerate()
    return PluginResult.ok({"count": len(ports), "ports": [p.to_dict() for p in ports]})


def tool_info(payload: dict[str, Any]) -> PluginResult:
    port = payload.get("port")
    if not port:
        return PluginResult.fail("missing 'port'")
    sp = get_serial_manager().get(port)
    if sp is None:
        return PluginResult.fail(f"unknown port: {port}")
    return PluginResult.ok(sp.to_dict())


def tool_connect(payload: dict[str, Any]) -> PluginResult:
    result = serial_actions.serial_connect(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_disconnect(payload: dict[str, Any]) -> PluginResult:
    result = serial_actions.serial_disconnect(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_allow(payload: dict[str, Any]) -> PluginResult:
    result = serial_actions.serial_allow(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


def tool_deny(payload: dict[str, Any]) -> PluginResult:
    result = serial_actions.serial_deny(payload)
    if "error" in result:
        return PluginResult.fail(result["error"])
    return PluginResult.ok(result)


SERIAL_TOOLS: list[PluginCapability] = [
    PluginCapability(
        name="serial.enumerate",
        description="List all available serial ports with metadata (UART/COM/ttyUSB/ttyACM).",
        permissions={"device.status"},
        executor=tool_enumerate,
    ),
    PluginCapability(
        name="serial.info",
        description="Get detailed information about a specific serial port.",
        permissions={"device.status"},
        executor=tool_info,
    ),
    PluginCapability(
        name="serial.connect",
        description="Connect to a serial port at a given baud rate.",
        permissions={"device.connect"},
        executor=tool_connect,
    ),
    PluginCapability(
        name="serial.disconnect",
        description="Disconnect from a serial port.",
        permissions={"device.disconnect"},
        executor=tool_disconnect,
    ),
    PluginCapability(
        name="serial.allow",
        description="Grant access to a serial port for the given capabilities.",
        permissions={"device.connect"},
        executor=tool_allow,
    ),
    PluginCapability(
        name="serial.deny",
        description="Deny access to a serial port.",
        permissions={"device.connect"},
        executor=tool_deny,
    ),
]


def invoke(tool_name: str, payload: dict[str, Any]) -> PluginResult:
    for tool in SERIAL_TOOLS:
        if tool.name == tool_name and tool.executor is not None:
            return tool.executor(payload)
    return PluginResult.fail(f"unknown serial tool: {tool_name}")
