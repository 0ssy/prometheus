"""ADB (Android Debug Bridge) capability permission system.

Gates access to Android devices by ADB serial and capability. Defaults to a
deny-unknown policy so the platform never shells into, reboots, or flashes a
device without an explicit allow rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AdbCapability(str, Enum):
    DISCOVER = "discover"
    READ_INFO = "read_info"
    SHELL = "shell"
    LOGCAT = "logcat"
    PUSH = "push"
    PULL = "pull"
    INSTALL = "install"
    REBOOT = "reboot"
    RECOVERY = "recovery"
    SIDELOAD = "sideload"


@dataclass
class AdbAllowRule:
    serial: Optional[str] = None
    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    capabilities: frozenset[AdbCapability] = field(
        default_factory=lambda: frozenset(AdbCapability)
    )

    def matches(
        self, serial: str, vendor_id: Optional[int], product_id: Optional[int]
    ) -> bool:
        if self.serial is not None and self.serial != serial:
            return False
        if self.vendor_id is not None and self.vendor_id != vendor_id:
            return False
        if self.product_id is not None and self.product_id != product_id:
            return False
        return True


@dataclass
class AdbDenyRule:
    serial: Optional[str] = None
    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    reason: str = "denied by policy"

    def matches(
        self, serial: str, vendor_id: Optional[int], product_id: Optional[int]
    ) -> bool:
        if self.serial is not None and self.serial != serial:
            return False
        if self.vendor_id is not None and self.vendor_id != vendor_id:
            return False
        if self.product_id is not None and self.product_id != product_id:
            return False
        return True


class AdbPermissionPolicy:
    """Allow/deny policy for ADB device access.

    Evaluation order: explicit deny first, then allow. If no allow rule
    matches, access is denied (safe default).
    """

    def __init__(self, default_allow: bool = False) -> None:
        self.default_allow = default_allow
        self.allow_rules: list[AdbAllowRule] = []
        self.deny_rules: list[AdbDenyRule] = []

    def allow(
        self,
        serial: Optional[str] = None,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        capabilities: Optional[frozenset[AdbCapability]] = None,
    ) -> None:
        self.allow_rules.append(
            AdbAllowRule(
                serial=serial,
                vendor_id=vendor_id,
                product_id=product_id,
                capabilities=capabilities
                if capabilities is not None
                else frozenset(AdbCapability),
            )
        )

    def deny(
        self,
        serial: Optional[str] = None,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        reason: str = "denied by policy",
    ) -> None:
        self.deny_rules.append(
            AdbDenyRule(
                serial=serial,
                vendor_id=vendor_id,
                product_id=product_id,
                reason=reason,
            )
        )

    def check(
        self,
        capability: AdbCapability,
        serial: str,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
    ) -> tuple[bool, str]:
        for rule in self.deny_rules:
            if rule.matches(serial, vendor_id, product_id):
                return False, rule.reason

        # Allowed if any matching allow rule grants the requested capability.
        # Rules that match but omit the capability are ignored so multiple
        # allow rules can grant different capability subsets.
        denied_reason: str | None = None
        for rule in self.allow_rules:
            if rule.matches(serial, vendor_id, product_id):
                if capability in rule.capabilities:
                    return True, "allowed by rule"
                denied_reason = f"capability '{capability.value}' not permitted for this device"

        if self.default_allow:
            return True, "allowed by default policy"
        return False, denied_reason or "no matching allow rule (default deny)"
