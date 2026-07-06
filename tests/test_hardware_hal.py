from __future__ import annotations

import pytest

from hardware.hal.manager import HALManager
from hardware.hal.registry import HardwareRegistry
from hardware.hal.capability_mapper import CapabilityMapper
from hardware.hal.interface import HardwareInterface
from hardware.drivers.usb import USBDriver
from hardware.drivers.adb import ADBDriver


class StubInterface(HardwareInterface):
    def connect(self) -> dict:
        return {}

    def disconnect(self) -> dict:
        return {}

    def identify(self) -> dict:
        return {}

    def capabilities(self) -> list:
        return []

    def execute(self, capability: str, payload: dict) -> dict:
        return {}

    def health(self) -> dict:
        return {}

    def diagnostics(self) -> dict:
        return {}


def test_hal_manager_register_and_get():
    manager = HALManager()
    interface = StubInterface()
    manager.register_interface("stub", interface)
    assert manager.get_interface("stub") is interface


def test_hal_manager_list_and_unregister():
    manager = HALManager()
    interface = StubInterface()
    manager.register_interface("stub", interface)
    assert "stub" in manager.list_interfaces()
    manager.unregister_interface("stub")
    assert "stub" not in manager.list_interfaces()


def test_hal_manager_get_missing_raises():
    manager = HALManager()
    with pytest.raises(KeyError):
        manager.get_interface("missing")


def test_hardware_registry_register_and_list():
    registry = HardwareRegistry()
    registry.register(USBDriver)
    assert "usb" in registry.list_registered()
    assert registry.get("usb") is USBDriver


def test_hardware_registry_discover_capabilities():
    registry = HardwareRegistry()
    registry.register(USBDriver)
    caps = registry.discover_capabilities("usb")
    assert "connect" in caps


def test_hardware_registry_singleton():
    HardwareRegistry._instance = None
    registry1 = HardwareRegistry.instance()
    registry2 = HardwareRegistry.instance()
    assert registry1 is registry2


def test_capability_mapper_register_and_map():
    mapper = CapabilityMapper()
    mapper.register_mapping("usb", {"read": "prometheus.read", "write": "prometheus.write"})
    mapped = mapper.map_interface_capabilities("usb", ["read", "write", "unknown"])
    assert mapped == ["prometheus.read", "prometheus.write", "unknown"]


def test_capability_mapper_get_prometheus_capabilities():
    mapper = CapabilityMapper()
    mapper.register_mapping("adb", {"shell": "prometheus.shell", "push": "prometheus.push"})
    caps = mapper.get_prometheus_capabilities("adb")
    assert set(caps) == {"prometheus.shell", "prometheus.push"}
