"""Prometheus SDK — Fastboot capability client.

Thin, stable SDK surface over the Fastboot Hardware API. Applications,
plugins, and automation steps use this instead of reaching into
``hardware.fastboot``.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from hardware.fastboot import (
    FastbootManager,
    FastbootCapability,
    FastbootDevice,
    FastbootPermissionPolicy,
    get_fastboot_manager,
)


class Fastboot:
    """SDK client for the Fastboot capability."""

    def __init__(self, manager: Optional[FastbootManager] = None) -> None:
        self._manager = manager or get_fastboot_manager()

    @property
    def manager(self) -> FastbootManager:
        return self._manager

    def enumerate(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._manager.enumerate()]

    def list(self) -> list[dict[str, Any]]:
        return self._manager.list()

    def get(self, serial: str) -> Optional[dict[str, Any]]:
        dev = self._manager.get(serial)
        return dev.to_dict() if dev else None

    def devices(self) -> list[FastbootDevice]:
        return self._manager.enumerate()

    def policy(self) -> FastbootPermissionPolicy:
        return self._manager.policy()

    def can_access(
        self,
        capability: str,
        serial: str,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
    ) -> tuple[bool, str]:
        cap = capability if isinstance(capability, FastbootCapability) else FastbootCapability(capability)
        return self._manager.can_access(cap, serial, vendor_id, product_id)

    def getvar(self, serial: str, variable: str = "all") -> dict[str, Any]:
        return self._manager.getvar(serial, variable=variable)

    def unlock(self, serial: str) -> dict[str, Any]:
        return self._manager.unlock(serial)

    def lock(self, serial: str) -> dict[str, Any]:
        return self._manager.lock(serial)

    def flash(self, serial: str, partition: str, image: str) -> dict[str, Any]:
        return self._manager.flash(serial, partition, image)

    def erase(self, serial: str, partition: str) -> dict[str, Any]:
        return self._manager.erase(serial, partition)

    def boot(self, serial: str, image: str) -> dict[str, Any]:
        return self._manager.boot(serial, image)

    def reboot(self, serial: str, mode: str = "normal") -> dict[str, Any]:
        return self._manager.reboot(serial, mode=mode)

    def allow(
        self,
        serial: Optional[str] = None,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        capabilities: Optional[set[str]] = None,
    ) -> None:
        caps = (
            frozenset(FastbootCapability(c) for c in capabilities)
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
