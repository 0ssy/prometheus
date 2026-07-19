"""Prometheus SDK — ADB (Android Debug Bridge) capability client.

Thin, stable SDK surface over the ADB Hardware API. Applications, plugins, and
automation steps use this instead of reaching into `hardware.adb`.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from hardware.adb import (
    ADBManager,
    AdbCapability,
    AdbDevice,
    AdbPermissionPolicy,
    get_adb_manager,
)


class ADB:
    """SDK client for the ADB capability."""

    def __init__(self, manager: Optional[ADBManager] = None) -> None:
        self._manager = manager or get_adb_manager()

    @property
    def manager(self) -> ADBManager:
        return self._manager

    def enumerate(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._manager.enumerate()]

    def list(self) -> list[dict[str, Any]]:
        return self._manager.list()

    def get(self, serial: str) -> Optional[dict[str, Any]]:
        dev = self._manager.get(serial)
        return dev.to_dict() if dev else None

    def devices(self) -> list[AdbDevice]:
        return self._manager.enumerate()

    def policy(self) -> AdbPermissionPolicy:
        return self._manager.policy()

    def can_access(
        self,
        capability: str,
        serial: str,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
    ) -> tuple[bool, str]:
        cap = capability if isinstance(capability, AdbCapability) else AdbCapability(capability)
        return self._manager.can_access(cap, serial, vendor_id, product_id)

    def shell(self, serial: str, command: str) -> dict[str, Any]:
        return self._manager.shell(serial, command)

    def logcat(self, serial: str, lines: int = 100) -> dict[str, Any]:
        return self._manager.logcat(serial, lines=lines)

    def push(self, serial: str, local: str, remote: str) -> dict[str, Any]:
        return self._manager.push(serial, local, remote)

    def pull(self, serial: str, remote: str, local: str) -> dict[str, Any]:
        return self._manager.pull(serial, remote, local)

    def install(self, serial: str, apk_path: str) -> dict[str, Any]:
        return self._manager.install(serial, apk_path)

    def reboot(self, serial: str, mode: str = "normal") -> dict[str, Any]:
        return self._manager.reboot(serial, mode=mode)

    def sideload(self, serial: str, ota_path: str) -> dict[str, Any]:
        return self._manager.sideload(serial, ota_path)

    def allow(
        self,
        serial: Optional[str] = None,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        capabilities: Optional[set[str]] = None,
    ) -> None:
        caps = (
            frozenset(AdbCapability(c) for c in capabilities)
            if capabilities is not None
            else None
        )
        self._manager.policy().allow(
            serial=serial, vendor_id=vendor_id, product_id=product_id, capabilities=caps
        )

    def deny(
        self,
        serial: Optional[str] = None,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        reason: str = "denied by policy",
    ) -> None:
        self._manager.policy().deny(
            serial=serial, vendor_id=vendor_id, product_id=product_id, reason=reason
        )

    def start_monitor(self, interval: float = 2.0) -> None:
        self._manager.start_monitor(interval=interval)

    def stop_monitor(self) -> None:
        self._manager.stop_monitor()

    def on_change(self, handler: Callable[[str, bool], None]) -> None:
        self._manager.on_change(handler)
