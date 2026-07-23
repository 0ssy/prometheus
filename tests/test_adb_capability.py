"""Tests for the ADB (Android Debug Bridge) capability (Capability 3).

Covers the permission system, the Hardware API (discovery, shell/logcat/push/
pull/install/reboot/recovery/sideload, hot-plug events), the SDK client, the
automation actions, the assistant tools, and the driver bridge. The manager
runs against its simulated backend here so the suite is hermetic.
"""

from __future__ import annotations

from hardware.adb import (
    AdbCapability,
    AdbPermissionPolicy,
    ADBManager,
    get_adb_manager,
)
from hardware.events import DeviceConnectedEvent, DeviceDisconnectedEvent
from core.event_bus import InMemoryEventBus

from sdk.adb import ADB
from automation.actions import adb_actions
from assistant.tools import adb_tools


class TestAdbPermissions:
    def test_default_deny(self):
        policy = AdbPermissionPolicy(default_allow=False)
        ok, why = policy.check(AdbCapability.SHELL, "ABCD1234")
        assert ok is False
        assert "default deny" in why

    def test_explicit_allow_by_serial(self):
        policy = AdbPermissionPolicy()
        policy.allow(serial="ABCD1234")
        ok, _ = policy.check(AdbCapability.SHELL, "ABCD1234")
        assert ok is True
        ok_other, _ = policy.check(AdbCapability.SHELL, "ZZZZ9999")
        assert ok_other is False

    def test_deny_overrides_allow(self):
        policy = AdbPermissionPolicy()
        policy.allow(serial="ABCD1234")
        policy.deny(serial="ABCD1234", reason="blocked")
        ok, why = policy.check(AdbCapability.SHELL, "ABCD1234")
        assert ok is False
        assert why == "blocked"

    def test_capability_scoped_allow(self):
        policy = AdbPermissionPolicy()
        policy.allow(serial="ABCD1234", capabilities=frozenset({AdbCapability.SHELL}))
        ok_shell, _ = policy.check(AdbCapability.SHELL, "ABCD1234")
        ok_flash, _ = policy.check(AdbCapability.SIDELOAD, "ABCD1234")
        assert ok_shell is True
        assert ok_flash is False


class TestAdbHardwareApi:
    def test_enumerate_returns_devices(self):
        manager = ADBManager(event_bus=InMemoryEventBus())
        devices = manager.enumerate()
        assert len(devices) >= 1
        assert all(d.serial for d in devices)

    def test_device_model_to_dict(self):
        manager = ADBManager(event_bus=InMemoryEventBus())
        dev = manager.enumerate()[0]
        d = dev.to_dict()
        assert d["serial"] == dev.serial
        assert "android_version" in d

    def test_shell_requires_permission(self):
        manager = ADBManager(event_bus=InMemoryEventBus())
        dev = manager.enumerate()[0]
        result = manager.shell(dev.serial, "getprop")
        assert result["status"] == "denied"
        manager.policy().allow(
            serial=dev.serial, capabilities=frozenset({AdbCapability.SHELL})
        )
        result2 = manager.shell(dev.serial, "getprop")
        assert result2["status"] == "simulated"

    def test_reboot_recovery_uses_recovery_capability(self):
        manager = ADBManager(event_bus=InMemoryEventBus())
        dev = manager.enumerate()[0]
        # Allow REBOOT but not RECOVERY -> recovery reboot must be denied.
        manager.policy().allow(
            serial=dev.serial, capabilities=frozenset({AdbCapability.REBOOT})
        )
        result = manager.reboot(dev.serial, mode="recovery")
        assert result["status"] == "denied"
        manager.policy().allow(
            serial=dev.serial, capabilities=frozenset({AdbCapability.RECOVERY})
        )
        result2 = manager.reboot(dev.serial, mode="recovery")
        assert result2["status"] == "simulated"

    def test_hotplug_detects_connect(self):
        bus = InMemoryEventBus()
        connected: list[DeviceConnectedEvent] = []
        bus.subscribe("hardware.device.connected", lambda e: connected.append(e))
        manager = ADBManager(event_bus=bus)
        manager._devices = {}
        manager.poll_once()
        assert len(connected) == len(manager.enumerate())


class TestAdbSdk:
    def test_sdk_enumerate(self):
        client = ADB(manager=ADBManager(event_bus=InMemoryEventBus()))
        devices = client.enumerate()
        assert len(devices) >= 1
        assert "serial" in devices[0]

    def test_sdk_access_respects_policy(self):
        client = ADB(manager=ADBManager(event_bus=InMemoryEventBus()))
        ok, _ = client.can_access("shell", "ABCD1234")
        assert ok is False
        client.allow(serial="ABCD1234")
        ok2, _ = client.can_access("shell", "ABCD1234")
        assert ok2 is True


class TestAdbAutomation:
    def test_enumerate_action(self):
        result = adb_actions.run_adb_action("adb:enumerate", {})
        assert "count" in result
        assert "devices" in result

    def test_shell_action(self):
        manager = get_adb_manager()
        dev = manager.enumerate()[0]
        manager.policy().allow(
            serial=dev.serial, capabilities=frozenset({AdbCapability.SHELL})
        )
        result = adb_actions.run_adb_action("adb:shell", {"serial": dev.serial, "command": "id"})
        assert result.get("status") == "simulated"

    def test_unknown_action(self):
        result = adb_actions.run_adb_action("adb:nope", {})
        assert "error" in result


class TestAdbAssistantTools:
    def test_enumerate_tool(self):
        result = adb_tools.invoke("adb.enumerate", {})
        assert result.success is True
        assert "devices" in result.data

    def test_shell_tool_unknown_device(self):
        result = adb_tools.invoke("adb.shell", {"serial": "nope", "command": "id"})
        assert result.success is False

    def test_unknown_tool(self):
        result = adb_tools.invoke("adb.missing", {})
        assert result.success is False

    def test_all_tools_have_executors(self):
        for tool in adb_tools.ADB_TOOLS:
            assert tool.executor is not None
            assert tool.permissions
