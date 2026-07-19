"""
RC6 recovery + firmware capability registration.

Registers recovery and firmware parsing capabilities on the
``CapabilityApi`` surface so the Rust Aether ``ToolDispatcher`` has
something to call:

    recovery.adb / recovery.fastboot / recovery.edl / recovery.dfu
    recovery.bios / recovery.uefi
    firmware.parse.elf / firmware.parse.bin / firmware.parse.hex
    firmware.parse.uf2 / firmware.parse.dfu / firmware.detect

Each capability delegates to ``recovery.unified`` or ``firmware.parsers``
and carries the exact permission set the ``Authorizer`` requires.
"""

from __future__ import annotations

from typing import Any

from core.logger import get_logger
from firmware.parsers import (
    detect_format,
    parse_bin,
    parse_dfu,
    parse_elf,
    parse_hex,
    parse_uf2,
)
from recovery.unified import UnifiedRecoveryFramework

logger = get_logger(__name__)

_RECOVERY_PERMISSIONS: set[str] = {"device.recover", "ownership_declared"}
_FIRMWARE_PERMISSIONS: set[str] = {"firmware.read"}

_RECOVERY_MODES = ("adb", "fastboot", "edl", "dfu", "bios", "uefi")


def _forwarding_executor(executor, permissions: set[str]):
    def wrapper(payload: dict[str, Any]) -> dict[str, Any]:
        payload = dict(payload)
        payload.setdefault("_permissions", set(permissions))
        return executor(payload)

    return wrapper


def register_recovery_capabilities(cap_api) -> None:
    framework = UnifiedRecoveryFramework()

    def make_recovery_executor(mode: str):
        def executor(payload: dict[str, Any]) -> dict[str, Any]:
            device_id = payload.get("device_id", "virtual-0")
            risk = payload.get("risk", "high")
            return framework.recover(device_id=device_id, mode=mode, risk=risk)

        return executor

    def make_firmware_executor(fn):
        def executor(payload: dict[str, Any]) -> dict[str, Any]:
            data = payload.get("data", b"")
            if isinstance(data, str):
                data = data.encode()
            return fn(data)

        return executor

    executors: dict[str, Any] = {}
    permissions: dict[str, set[str]] = {}

    for mode in _RECOVERY_MODES:
        name = f"recovery.{mode}"
        executors[name] = make_recovery_executor(mode)
        permissions[name] = set(_RECOVERY_PERMISSIONS)

    firmware_parsers = {
        "firmware.parse.elf": parse_elf,
        "firmware.parse.bin": parse_bin,
        "firmware.parse.hex": parse_hex,
        "firmware.parse.uf2": parse_uf2,
        "firmware.parse.dfu": parse_dfu,
    }
    for name, fn in firmware_parsers.items():
        executors[name] = make_firmware_executor(fn)
        permissions[name] = set(_FIRMWARE_PERMISSIONS)

    def detect_executor(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data", b"")
        if isinstance(data, str):
            data = data.encode()
        return {"format": detect_format(data), "size": len(data)}

    executors["firmware.detect"] = detect_executor
    permissions["firmware.detect"] = set(_FIRMWARE_PERMISSIONS)

    target = "recovery"
    for name, executor in executors.items():
        if cap_api.exists(name):
            continue
        cap_api.register(
            name=name,
            target=target,
            description=f"Recovery/firmware capability: {name}",
            permissions=set(permissions[name]),
            executor=_forwarding_executor(executor, permissions[name]),
        )
    logger.info("Registered %d recovery/firmware capabilities", len(executors))
