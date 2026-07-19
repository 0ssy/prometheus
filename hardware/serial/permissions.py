"""Serial communication capability permission system.

Gates access to serial ports by port path, USB VID/PID, and capability.
Defaults to a deny-unknown policy so the platform never claims a serial
port (which may be a console, modem, or bootloader) without an explicit rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SerialCapability(str, Enum):
    ENUMERATE = "enumerate"
    READ_INFO = "read_info"
    CONNECT = "connect"
    READ = "read"
    WRITE = "write"
    CONFIGURE = "configure"
    LOG = "log"


@dataclass
class SerialAllowRule:
    port: Optional[str] = None
    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    serial: Optional[str] = None
    capabilities: frozenset[SerialCapability] = field(
        default_factory=lambda: frozenset(SerialCapability)
    )

    def matches(
        self,
        port: str,
        vendor_id: Optional[int],
        product_id: Optional[int],
        serial: Optional[str],
    ) -> bool:
        if self.port is not None and self.port != port:
            return False
        if self.vendor_id is not None and self.vendor_id != vendor_id:
            return False
        if self.product_id is not None and self.product_id != product_id:
            return False
        if self.serial is not None and self.serial != serial:
            return False
        return True


@dataclass
class SerialDenyRule:
    port: Optional[str] = None
    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    serial: Optional[str] = None
    reason: str = "denied by policy"

    def matches(
        self,
        port: str,
        vendor_id: Optional[int],
        product_id: Optional[int],
        serial: Optional[str],
    ) -> bool:
        if self.port is not None and self.port != port:
            return False
        if self.vendor_id is not None and self.vendor_id != vendor_id:
            return False
        if self.product_id is not None and self.product_id != product_id:
            return False
        if self.serial is not None and self.serial != serial:
            return False
        return True


class SerialPermissionPolicy:
    """Allow/deny policy for serial port access.

    Evaluation order: explicit deny first, then allow. If no allow rule
    matches, access is denied (safe default).
    """

    def __init__(self, default_allow: bool = False) -> None:
        self.default_allow = default_allow
        self.allow_rules: list[SerialAllowRule] = []
        self.deny_rules: list[SerialDenyRule] = []

    def allow(
        self,
        port: Optional[str] = None,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        serial: Optional[str] = None,
        capabilities: Optional[frozenset[SerialCapability]] = None,
    ) -> None:
        self.allow_rules.append(
            SerialAllowRule(
                port=port,
                vendor_id=vendor_id,
                product_id=product_id,
                serial=serial,
                capabilities=capabilities
                if capabilities is not None
                else frozenset(SerialCapability),
            )
        )

    def deny(
        self,
        port: Optional[str] = None,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        serial: Optional[str] = None,
        reason: str = "denied by policy",
    ) -> None:
        self.deny_rules.append(
            SerialDenyRule(
                port=port,
                vendor_id=vendor_id,
                product_id=product_id,
                serial=serial,
                reason=reason,
            )
        )

    def check(
        self,
        capability: SerialCapability,
        port: str,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
        serial: Optional[str] = None,
    ) -> tuple[bool, str]:
        for rule in self.deny_rules:
            if rule.matches(port, vendor_id, product_id, serial):
                return False, rule.reason

        for rule in self.allow_rules:
            if rule.matches(port, vendor_id, product_id, serial):
                if capability in rule.capabilities:
                    return True, "allowed by rule"
                return (
                    False,
                    f"capability '{capability.value}' not permitted for this port",
                )

        if self.default_allow:
            return True, "allowed by default policy"
        return False, "no matching allow rule (default deny)"
