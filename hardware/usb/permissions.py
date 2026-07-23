"""USB capability permission system.

Gates access to connected USB devices by vendor/product id, serial number,
and capability. Defaults to a deny-unknown policy so that no device can be
claimed without an explicit allow rule — this is the safe posture for a
platform that may one day flash firmware or wipe storage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class UsbCapability(str, Enum):
    ENUMERATE = "enumerate"
    READ_INFO = "read_info"
    CONNECT = "connect"
    READ = "read"
    WRITE = "write"
    FLASH = "flash"
    REBOOT = "reboot"


@dataclass
class UsbAllowRule:
    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    serial: Optional[str] = None
    capabilities: frozenset[UsbCapability] = field(
        default_factory=lambda: frozenset(UsbCapability)
    )

    def matches(self, vendor_id: int, product_id: int, serial: Optional[str]) -> bool:
        if self.vendor_id is not None and self.vendor_id != vendor_id:
            return False
        if self.product_id is not None and self.product_id != product_id:
            return False
        if self.serial is not None and self.serial != serial:
            return False
        return True


@dataclass
class UsbDenyRule:
    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    serial: Optional[str] = None
    reason: str = "denied by policy"

    def matches(self, vendor_id: int, product_id: int, serial: Optional[str]) -> bool:
        if self.vendor_id is not None and self.vendor_id != vendor_id:
            return False
        if self.product_id is not None and self.product_id != product_id:
            return False
        if self.serial is not None and self.serial != serial:
            return False
        return True


class UsbPermissionPolicy:
    """Allow/deny policy for USB device access.

    Evaluation order: explicit deny first, then allow. If no allow rule
    matches, access is denied (safe default).
    """

    def __init__(self, default_allow: bool = False) -> None:
        self.default_allow = default_allow
        self.allow_rules: list[UsbAllowRule] = []
        self.deny_rules: list[UsbDenyRule] = []

    def allow(
        self,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        serial: Optional[str] = None,
        capabilities: Optional[frozenset[UsbCapability]] = None,
    ) -> None:
        self.allow_rules.append(
            UsbAllowRule(
                vendor_id=vendor_id,
                product_id=product_id,
                serial=serial,
                capabilities=capabilities
                if capabilities is not None
                else frozenset(UsbCapability),
            )
        )

    def deny(
        self,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        serial: Optional[str] = None,
        reason: str = "denied by policy",
    ) -> None:
        self.deny_rules.append(
            UsbDenyRule(
                vendor_id=vendor_id, product_id=product_id, serial=serial, reason=reason
            )
        )

    def check(
        self,
        capability: UsbCapability,
        vendor_id: int,
        product_id: int,
        serial: Optional[str] = None,
    ) -> tuple[bool, str]:
        for rule in self.deny_rules:
            if rule.matches(vendor_id, product_id, serial):
                return False, rule.reason

        # Allowed if any matching allow rule grants the requested capability.
        # Rules that match but omit the capability are ignored so multiple
        # allow rules can grant different capability subsets.
        denied_reason: str | None = None
        for rule in self.allow_rules:
            if rule.matches(vendor_id, product_id, serial):
                if capability in rule.capabilities:
                    return True, "allowed by rule"
                denied_reason = f"capability '{capability.value}' not permitted for this device"

        if self.default_allow:
            return True, "allowed by default policy"
        return False, denied_reason or "no matching allow rule (default deny)"
