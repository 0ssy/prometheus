"""
Ownership Gate (RFC 0000)
-----------------------------------------
Decision, accepted for v0.1: DECLARED ownership only. Device.ownership_declared
is an honor-system flag set at registration time — NOT a verified guarantee.

Every module that does more than basic connect/read/write on a device — this
means every Gamma module: Firmware Inspector, Partition Mapper, Boot Chain
Analyzer, Recovery Planner — MUST call require_ownership_declared() before
touching the device. This is the actual code-level gate RFC 0000 promised,
not a comment telling some future version of you to add one later.
"""

from core.logger import get_logger
from devices.base import Device

logger = get_logger(__name__)


class OwnershipNotDeclaredError(PermissionError):
    pass


def require_ownership_declared(device: Device) -> None:
    if not device.ownership_declared:
        logger.warning(
            f"Blocked action on device {device.device_id}: ownership not declared"
        )
        raise OwnershipNotDeclaredError(
            f"Device {device.device_id} has no declared ownership. "
            f"This device must be registered with ownership_declared=True "
            f"before any Gamma-level inspection or recovery action can run."
        )
