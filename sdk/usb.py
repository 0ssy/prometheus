"""Prometheus SDK — USB capability client.

Thin, stable SDK surface over the USB Hardware API. Applications, plugins,
and automation steps use this instead of reaching into `hardware.usb`
directly, so the contract can evolve without breaking callers.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from hardware.usb import (
    USBManager,
    UsbCapability,
    UsbDevice,
    UsbPermissionPolicy,
    get_usb_manager,
)


class Usb:
    """SDK client for the USB capability."""

    def __init__(self, manager: Optional[USBManager] = None) -> None:
        self._manager = manager or get_usb_manager()

    @property
    def manager(self) -> USBManager:
        return self._manager

    def enumerate(self) -> list[dict[str, Any]]:
        """List all currently attached USB devices."""
        return [d.to_dict() for d in self._manager.enumerate()]

    def list(self) -> list[dict[str, Any]]:
        return self._manager.list()

    def get(self, device_id: str) -> Optional[dict[str, Any]]:
        dev = self._manager.get(device_id)
        return dev.to_dict() if dev else None

    def devices(self) -> list[UsbDevice]:
        return self._manager.enumerate()

    def policy(self) -> UsbPermissionPolicy:
        return self._manager.policy()

    def can_access(
        self,
        capability: str,
        vendor_id: int,
        product_id: int,
        serial: Optional[str] = None,
    ) -> tuple[bool, str]:
        cap = UsbCapability(capability) if not isinstance(capability, UsbCapability) else capability
        return self._manager.can_access(cap, vendor_id, product_id, serial)

    def allow(
        self,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        serial: Optional[str] = None,
        capabilities: Optional[set[str]] = None,
    ) -> None:
        caps = (
            frozenset(UsbCapability(c) for c in capabilities)
            if capabilities is not None
            else None
        )
        self._manager.policy().allow(
            vendor_id=vendor_id, product_id=product_id, serial=serial, capabilities=caps
        )

    def deny(
        self,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        serial: Optional[str] = None,
        reason: str = "denied by policy",
    ) -> None:
        self._manager.policy().deny(
            vendor_id=vendor_id, product_id=product_id, serial=serial, reason=reason
        )

    def start_monitor(self, interval: float = 1.0) -> None:
        self._manager.start_monitor(interval=interval)

    def stop_monitor(self) -> None:
        self._manager.stop_monitor()

    def on_change(self, handler: Callable[[str, bool], None]) -> None:
        self._manager.on_change(handler)
