"""Tests for the Serial communication capability (Capability 2).

Covers the permission system, the Hardware API (enumeration, connect/IO,
hot-plug events, logging), the SDK client, the automation actions, and the
assistant tools. The manager runs against its simulated backend here so the
suite is hermetic and does not depend on attached serial hardware.
"""

from __future__ import annotations

from hardware.serial import (
    SerialCapability,
    SerialPermissionPolicy,
    SerialManager,
    get_serial_manager,
)
from hardware.events import DeviceConnectedEvent, DeviceDisconnectedEvent
from core.event_bus import InMemoryEventBus

from sdk.serial import Serial
from automation.actions import serial_actions
from assistant.tools import serial_tools


class TestSerialPermissions:
    def test_default_deny(self):
        policy = SerialPermissionPolicy(default_allow=False)
        ok, why = policy.check(SerialCapability.CONNECT, "COM3")
        assert ok is False
        assert "default deny" in why

    def test_explicit_allow_by_port(self):
        policy = SerialPermissionPolicy()
        policy.allow(port="COM3")
        ok, _ = policy.check(SerialCapability.CONNECT, "COM3")
        assert ok is True
        ok_other, _ = policy.check(SerialCapability.CONNECT, "COM4")
        assert ok_other is False

    def test_deny_overrides_allow(self):
        policy = SerialPermissionPolicy()
        policy.allow(port="COM3")
        policy.deny(port="COM3", reason="blocked")
        ok, why = policy.check(SerialCapability.CONNECT, "COM3")
        assert ok is False
        assert why == "blocked"

    def test_capability_scoped_allow(self):
        policy = SerialPermissionPolicy()
        policy.allow(port="COM3", capabilities=frozenset({SerialCapability.READ_INFO}))
        ok_read, _ = policy.check(SerialCapability.READ_INFO, "COM3")
        ok_write, _ = policy.check(SerialCapability.WRITE, "COM3")
        assert ok_read is True
        assert ok_write is False


class TestSerialHardwareApi:
    def test_enumerate_returns_ports(self):
        manager = SerialManager(event_bus=InMemoryEventBus())
        ports = manager.enumerate()
        assert len(ports) >= 1
        assert all(p.port for p in ports)

    def test_port_model_to_dict(self):
        manager = SerialManager(event_bus=InMemoryEventBus())
        port = manager.enumerate()[0]
        d = port.to_dict()
        assert d["port"] == port.port
        assert "baud_rates" in d

    def test_connect_requires_permission(self):
        manager = SerialManager(event_bus=InMemoryEventBus())
        port = manager.enumerate()[0]
        result = manager.connect(port.port)
        assert result["status"] == "denied"
        manager.policy().allow(
            port=port.port,
            vendor_id=port.vendor_id,
            product_id=port.product_id,
            serial=port.serial_number,
            capabilities=frozenset({SerialCapability.CONNECT, SerialCapability.WRITE}),
        )
        result2 = manager.connect(port.port, baud_rate=9600)
        assert result2["status"] == "connected"
        assert manager.get(port.port).connected is True

    def test_read_write_logs(self):
        manager = SerialManager(event_bus=InMemoryEventBus())
        port = manager.enumerate()[0]
        manager.policy().allow(
            port=port.port,
            capabilities=frozenset({SerialCapability.CONNECT, SerialCapability.WRITE, SerialCapability.READ}),
        )
        manager.connect(port.port)
        n = manager.write(port.port, b"AT\r\n")
        assert n == 4
        assert manager.read(port.port) == b""
        entries = manager.log()
        assert any(e["kind"] == "write" for e in entries)

    def test_hotplug_detects_connect(self):
        bus = InMemoryEventBus()
        connected: list[DeviceConnectedEvent] = []
        bus.subscribe("hardware.device.connected", lambda e: connected.append(e))
        manager = SerialManager(event_bus=bus)
        manager._ports = {}
        manager.poll_once()
        assert len(connected) == len(manager.enumerate())


class TestSerialSdk:
    def test_sdk_enumerate(self):
        client = Serial(manager=SerialManager(event_bus=InMemoryEventBus()))
        ports = client.enumerate()
        assert len(ports) >= 1
        assert "port" in ports[0]

    def test_sdk_access_respects_policy(self):
        client = Serial(manager=SerialManager(event_bus=InMemoryEventBus()))
        ok, _ = client.can_access("connect", "COM3")
        assert ok is False
        client.allow(port="COM3")
        ok2, _ = client.can_access("connect", "COM3")
        assert ok2 is True


class TestSerialAutomation:
    def test_enumerate_action(self):
        result = serial_actions.run_serial_action("serial:enumerate", {})
        assert "count" in result
        assert "ports" in result

    def test_connect_action(self):
        manager = get_serial_manager()
        port = manager.enumerate()[0]
        manager.policy().allow(
            port=port.port,
            vendor_id=port.vendor_id,
            product_id=port.product_id,
            serial=port.serial_number,
            capabilities=frozenset({SerialCapability.CONNECT}),
        )
        result = serial_actions.run_serial_action(
            "serial:connect", {"port": port.port, "baud_rate": 115200}
        )
        assert result.get("status") == "connected"

    def test_unknown_action(self):
        result = serial_actions.run_serial_action("serial:nope", {})
        assert "error" in result


class TestSerialAssistantTools:
    def test_enumerate_tool(self):
        result = serial_tools.invoke("serial.enumerate", {})
        assert result.success is True
        assert "ports" in result.data

    def test_info_tool_unknown(self):
        result = serial_tools.invoke("serial.info", {"port": "nope"})
        assert result.success is False

    def test_unknown_tool(self):
        result = serial_tools.invoke("serial.missing", {})
        assert result.success is False

    def test_all_tools_have_executors(self):
        for tool in serial_tools.SERIAL_TOOLS:
            assert tool.executor is not None
            assert tool.permissions
