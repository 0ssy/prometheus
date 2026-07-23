"""Fastboot capability permission system.

Gates access to fastboot-mode devices by serial and capability. Fastboot is
the most dangerous mode (it can erase and reflash firmware), so the policy
defaults to **deny-unknown** and treats unlock/flash/erase/boot as distinct,
explicitly-grantable capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FastbootCapability(str, Enum):
    DISCOVER = "discover"
    READ_INFO = "read_info"
    GETVAR = "getvar"
    UNLOCK = "unlock"
    LOCK = "lock"
    FLASH = "flash"
    ERASE = "erase"
    BOOT = "boot"
    REBOOT = "reboot"


@dataclass
class FastbootAllowRule:
    serial: Optional[str] = None
    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    capabilities: frozenset[FastbootCapability] = field(
        default_factory=lambda: frozenset(FastbootCapability)
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
class FastbootDenyRule:
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


class FastbootPermissionPolicy:
    """Allow/deny policy for fastboot device access.

    Evaluation order: explicit deny first, then allow (any matching rule that
    grants the capability), then default. With ``default_allow=False`` (the
    safe default) no device can be unlocked/flashed/erased/booted without an
    explicit allow rule.
    """

    def __init__(self, default_allow: bool = False) -> None:
        self.default_allow = default_allow
        self.allow_rules: list[FastbootAllowRule] = []
        self.deny_rules: list[FastbootDenyRule] = []

    def allow(
        self,
        serial: Optional[str] = None,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        capabilities: Optional[frozenset[FastbootCapability]] = None,
    ) -> None:
        self.allow_rules.append(
            FastbootAllowRule(
                serial=serial,
                vendor_id=vendor_id,
                product_id=product_id,
                capabilities=capabilities
                if capabilities is not None
                else frozenset(FastbootCapability),
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
            FastbootDenyRule(
                serial=serial,
                vendor_id=vendor_id,
                product_id=product_id,
                reason=reason,
            )
        )

    def check(
        self,
        capability: FastbootCapability,
        serial: str,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
    ) -> tuple[bool, str]:
        for rule in self.deny_rules:
            if rule.matches(serial, vendor_id, product_id):
                return False, rule.reason

        denied_reason: str | None = None
        for rule in self.allow_rules:
            if rule.matches(serial, vendor_id, product_id):
                if capability in rule.capabilities:
                    return True, "allowed by rule"
                denied_reason = f"capability '{capability.value}' not permitted for this device"

        if self.default_allow:
            return True, "allowed by default policy"
        return False, denied_reason or "no matching allow rule (default deny)"
