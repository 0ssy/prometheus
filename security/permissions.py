"""
Security: Permissions (Epsilon / Hephaestus phase)
-------------------------------------------------
Defines and manages the permission vocabulary used to gate hardware
operations. Hardware actions map to the permissions required to perform them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Permission:
    name: str
    description: str
    category: str
    requires_ownership: bool = False


class PermissionRegistry:
    def __init__(self) -> None:
        self._permissions: dict[str, Permission] = {}
        self._action_map: dict[str, set[str]] = {}
        self._lock = Lock()

    def register(self, permission: Permission) -> None:
        with self._lock:
            if permission.name in self._permissions:
                raise ValueError(f"Permission '{permission.name}' already registered")
            self._permissions[permission.name] = permission
        logger.info("Registered permission: %s", permission.name)

    def get(self, name: str) -> Permission | None:
        with self._lock:
            return self._permissions.get(name)

    def list_by_category(self, category: str) -> list[Permission]:
        with self._lock:
            return [
                permission
                for permission in self._permissions.values()
                if permission.category == category
            ]

    def list_all(self) -> list[Permission]:
        with self._lock:
            return list(self._permissions.values())

    def map_action(self, action: str, permissions: set[str]) -> None:
        with self._lock:
            self._action_map[action] = set(permissions)
        logger.info("Mapped action %s -> %s", action, sorted(permissions))

    def required_for(self, action: str) -> set[str]:
        with self._lock:
            return set(self._action_map.get(action, set()))


def _build_default_registry() -> PermissionRegistry:
    registry = PermissionRegistry()
    defaults = [
        Permission("device.connect", "connect to device", "device"),
        Permission("device.disconnect", "disconnect from device", "device"),
        Permission("device.read", "read from device", "device"),
        Permission("device.write", "write to device", "device"),
        Permission("device.status", "get device status", "device"),
        Permission("device.diagnose", "run diagnostics", "device"),
        Permission(
            "device.recover", "recovery planning", "device", requires_ownership=True
        ),
        Permission(
            "device.flash", "flash firmware", "device", requires_ownership=True
        ),
        Permission("device.reboot", "reboot device", "device", requires_ownership=True),
        Permission("device.simulate", "simulate device operation", "device"),
        Permission("ownership_declared", "ownership declared for resource", "hardware"),
        Permission("hardware.session.create", "create hardware session", "hardware"),
        Permission("hardware.session.close", "close hardware session", "hardware"),
        Permission("firmware.read", "read firmware metadata", "firmware"),
        Permission("firmware.parse", "parse firmware structure", "firmware"),
    ]
    for permission in defaults:
        registry.register(permission)

    action_mappings = [
        ("device.connect", {"device.connect"}),
        ("device.disconnect", {"device.disconnect"}),
        ("device.read", {"device.read"}),
        ("device.write", {"device.write"}),
        ("device.status", {"device.status"}),
        ("device.diagnose", {"device.diagnose"}),
        ("device.recover", {"device.recover", "ownership_declared"}),
        ("device.flash", {"device.flash", "ownership_declared"}),
        ("device.reboot", {"device.reboot", "ownership_declared"}),
        ("device.simulate", {"device.simulate"}),
        ("hardware.session.create", {"hardware.session.create"}),
        ("hardware.session.close", {"hardware.session.close"}),
        ("firmware.read", {"firmware.read"}),
        ("firmware.parse", {"firmware.parse"}),
    ]
    for action, perms in action_mappings:
        registry.map_action(action, perms)

    return registry


default_registry = _build_default_registry()
