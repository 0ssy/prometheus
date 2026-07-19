from __future__ import annotations

import pytest

from api.capability_api import CapabilityApi
from core.capabilities import CapabilityManager
from services.recovery_capabilities import register_recovery_capabilities

RECOVERY_CAPABILITIES = (
    "recovery.adb",
    "recovery.fastboot",
    "recovery.edl",
    "recovery.dfu",
    "recovery.bios",
    "recovery.uefi",
)

FIRMWARE_CAPABILITIES = (
    "firmware.parse.elf",
    "firmware.parse.bin",
    "firmware.parse.hex",
    "firmware.parse.uf2",
    "firmware.parse.dfu",
    "firmware.detect",
)

ALL_CAPABILITIES = RECOVERY_CAPABILITIES + FIRMWARE_CAPABILITIES

RECOVERY_PERMISSIONS = {"device.recover", "ownership_declared"}
FIRMWARE_PERMISSIONS = {"firmware.read"}


def _recognized(name: str) -> set[str]:
    return RECOVERY_PERMISSIONS if name.startswith("recovery.") else FIRMWARE_PERMISSIONS


def test_register_all_capabilities():
    manager = CapabilityManager()
    register_recovery_capabilities(manager)
    for name in ALL_CAPABILITIES:
        assert manager.exists(name)


def test_discover_prefix():
    manager = CapabilityManager()
    register_recovery_capabilities(manager)
    assert len(manager.discover(prefix="recovery.")) == len(RECOVERY_CAPABILITIES)
    assert len(manager.discover(prefix="firmware.")) == len(FIRMWARE_CAPABILITIES)


def test_permissions_required():
    manager = CapabilityManager()
    register_recovery_capabilities(manager)
    for name in ALL_CAPABILITIES:
        assert manager.authorize(name, _recognized(name))
        assert not manager.authorize(name, set())


def test_execute_recovery_capabilities():
    manager = CapabilityManager()
    register_recovery_capabilities(manager)
    for name in RECOVERY_CAPABILITIES:
        mode = name.split(".")[1]
        result = manager.execute(name, {"device_id": "dev1"}, RECOVERY_PERMISSIONS)
        assert result["mode"] == mode
        assert result["device_id"] == "dev1"
        assert result["status"] == "stub"
        assert result["risk"] == "high"


def test_execute_firmware_parse_capabilities():
    manager = CapabilityManager()
    register_recovery_capabilities(manager)
    for name in (
        "firmware.parse.elf",
        "firmware.parse.bin",
        "firmware.parse.hex",
        "firmware.parse.uf2",
        "firmware.parse.dfu",
    ):
        fmt = name.split(".")[2]
        result = manager.execute(name, {"data": b"payload"}, FIRMWARE_PERMISSIONS)
        assert result["format"] == fmt
        assert result["size"] == len(b"payload")
        assert result["status"] == "stub"


def test_execute_firmware_detect():
    manager = CapabilityManager()
    register_recovery_capabilities(manager)
    result = manager.execute("firmware.detect", {"data": b"\x7fELFdata"}, FIRMWARE_PERMISSIONS)
    assert result["format"] == "elf"
    assert result["size"] == len(b"\x7fELFdata")


def test_execute_denied_without_permissions():
    manager = CapabilityManager()
    register_recovery_capabilities(manager)
    with pytest.raises(PermissionError):
        manager.execute("recovery.adb", {"device_id": "dev1"}, set())
    with pytest.raises(PermissionError):
        manager.execute("firmware.parse.elf", {"data": b"x"}, set())
