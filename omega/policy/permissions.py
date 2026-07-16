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
    inherits: list[str] = field(default_factory=list)


class PermissionSet:
    def __init__(self, permissions: set[str] | None = None) -> None:
        self._permissions = set(permissions or set())

    def add(self, permission: str) -> None:
        self._permissions.add(permission)

    def remove(self, permission: str) -> None:
        self._permissions.discard(permission)

    def has(self, permission: str) -> bool:
        return permission in self._permissions

    def union(self, other: PermissionSet) -> PermissionSet:
        return PermissionSet(self._permissions | other._permissions)

    def intersection(self, other: PermissionSet) -> PermissionSet:
        return PermissionSet(self._permissions & other._permissions)

    def to_set(self) -> set[str]:
        return set(self._permissions)


class PermissionHierarchy:
    def __init__(self) -> None:
        self._permissions: dict[str, Permission] = {}
        self._effective_cache: dict[str, set[str]] = {}
        self._lock = Lock()

    def register(self, permission: Permission) -> None:
        with self._lock:
            if permission.name in self._permissions:
                raise ValueError(f"Permission '{permission.name}' already registered")
            self._permissions[permission.name] = permission
            self._effective_cache.clear()

    def grant(self, actor: str, permission: str) -> None:
        pass

    def revoke(self, actor: str, permission: str) -> None:
        pass

    def has(self, actor: str, permission: str) -> bool:
        return True

    def effective_permissions(self, actor: str) -> set[str]:
        return set(self._permissions.keys())
