"""Tests for the USB capability (Capability 1).

Covers the permission system, the Hardware API (enumeration, info,
hot-plug event emission), the SDK client, the automation actions, and the
assistant tools. The manager runs against its simulated backend here so the
suite is hermetic and does not depend on attached hardware.
"""

from __future__ import annotations

from hardware.usb import UsbCapability, UsbPermissionPolicy, USBManager, get_usb_manager
from hardware.events import DeviceConnectedEvent, DeviceDisconnectedEvent
from core.event_bus import InMemoryEventBus

from sdk.usb import Usb
from automation.actions import usb_actions
from assistant.tools import usb_tools


class TestUsbPermissions:
    def test_default_deny(self):
        policy = UsbPermissionPolicy(default_allow=False)
        ok, why = policy.check(UsbCapability.ENUMERATE, 0x1234, 0x5678)
        assert ok is False
        assert "default deny" in why

    def test_explicit_allow(self):
        policy = UsbPermissionPolicy()
        policy.allow(vendor_id=0x18D1, product_id=0x4EE7)
        ok, _ = policy.check(UsbCapability.ENUMERATE, 0x18D1, 0x4EE7)
        assert ok is True

    def test_deny_overrides_allow(self):
        policy = UsbPermissionPolicy()
        policy.allow(vendor_id=0x18D1, product_id=0x4EE7)
        policy.deny(vendor_id=0x18D1, product_id=0x4EE7, reason="blocked")
        ok, why = policy.check(UsbCapability.ENUMERATE, 0x18D1, 0x4EE7)
        assert ok is False
        assert why == "blocked"

    def test_capability_scoped_allow(self):
        policy = UsbPermissionPolicy()
        policy.allow(
            vendor_id=0x18D1,
            product_id=0x4EE7,
            capabilities=frozenset({UsbCapability.READ_INFO}),
        )
        ok_read, _ = policy.check(UsbCapability.READ_INFO, 0x18D1, 0x4EE7)
        ok_flash, _ = policy.check(UsbCapability.FLASH, 0x18D1, 0x4EE7)
        assert ok_read is True
        assert ok_flash is False

    def test_serial_matters(self):
        policy = UsbPermissionPolicy()
        policy.allow(vendor_id=0x18D1, product_id=0x4EE7, serial="ABC")
        ok_match, _ = policy.check(UsbCapability.ENUMERATE, 0x18D1, 0x4EE7, "ABC")
        ok_miss, _ = policy.check(UsbCapability.ENUMERATE, 0x18D1, 0x4EE7, "XYZ")
        assert ok_match is True
        assert ok_miss is False


class TestUsbHardwareApi:
    def test_enumerate_returns_devices(self):
        manager = USBManager(event_bus=InMemoryEventBus())
        devices = manager.enumerate()
        assert len(devices) >= 1
        assert all(d.vendor_id and d.product_id for d in devices)

    def test_device_model_to_dict(self):
        manager = USBManager(event_bus=InMemoryEventBus())
        dev = manager.enumerate()[0]
        d = dev.to_dict()
        assert d["vid_pid"] == dev.vid_pid
        assert d["connected"] is True

    def test_get_unknown_device(self):
        manager = USBManager(event_bus=InMemoryEventBus())
        manager.enumerate()
        assert manager.get("does-not-exist") is None

    def test_hotplug_emits_events(self):
        bus = InMemoryEventBus()
        connected: list[DeviceConnectedEvent] = []
        disconnected: list[DeviceDisconnectedEvent] = []
        bus.subscribe("hardware.device.connected", lambda e: connected.append(e))
        bus.subscribe("hardware.device.disconnected", lambda e: disconnected.append(e))

        manager = USBManager(event_bus=bus)
        manager.enumerate()
        manager.poll_once()

        # No devices were unplugged during the single snapshot, so the loop
        # should not emit spurious events.
        assert connected == []
        assert disconnected == []

    def test_hotplug_detects_connect(self):
        bus = InMemoryEventBus()
        connected: list[DeviceConnectedEvent] = []
        bus.subscribe("hardware.device.connected", lambda e: connected.append(e))

        manager = USBManager(event_bus=bus)
        # Seed with an empty device set, then enumerate (simulated devices appear).
        manager._devices = {}
        manager.poll_once()
        assert len(connected) == len(manager.enumerate())


class TestUsbSdk:
    def test_sdk_enumerate(self):
        client = Usb(manager=USBManager(event_bus=InMemoryEventBus()))
        devices = client.enumerate()
        assert len(devices) >= 1
        assert "vid_pid" in devices[0]

    def test_sdk_access_respects_policy(self):
        client = Usb(manager=USBManager(event_bus=InMemoryEventBus()))
        ok, _ = client.can_access("enumerate", 0x18D1, 0x4EE7)
        assert ok is False
        client.allow(vendor_id=0x18D1, product_id=0x4EE7)
        ok2, _ = client.can_access("enumerate", 0x18D1, 0x4EE7)
        assert ok2 is True


class TestUsbAutomation:
    def test_enumerate_action(self):
        result = usb_actions.run_usb_action("usb:enumerate", {})
        assert "count" in result
        assert "devices" in result

    def test_allow_action(self):
        result = usb_actions.run_usb_action(
            "usb:allow", {"vendor_id": "0x18d1", "product_id": "0x4ee7"}
        )
        assert result.get("status") == "allowed"

    def test_unknown_action(self):
        result = usb_actions.run_usb_action("usb:nope", {})
        assert "error" in result


class TestUsbAssistantTools:
    def test_enumerate_tool(self):
        result = usb_tools.invoke("usb.enumerate", {})
        assert result.success is True
        assert "devices" in result.data

    def test_info_tool_unknown(self):
        result = usb_tools.invoke("usb.info", {"device_id": "nope"})
        assert result.success is False

    def test_unknown_tool(self):
        result = usb_tools.invoke("usb.missing", {})
        assert result.success is False

    def test_all_tools_have_executors(self):
        for tool in usb_tools.USB_TOOLS:
            assert tool.executor is not None
            assert tool.permissions
