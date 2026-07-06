from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import threading

from core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class Permission:
    name: str
    description: str = ""
    category: str = "general"
    requires_ownership: bool = False
    inherits: list[str] = field(default_factory=list)


class PermissionSet:
    def __init__(self, permissions: set[str] | None = None) -> None:
        self._permissions = set(permissions or [])

    def add(self, permission: str) -> None:
        self._permissions.add(permission)

    def union(self, other: PermissionSet) -> PermissionSet:
        return PermissionSet(self._permissions | other._permissions)

    def intersection(self, other: PermissionSet) -> PermissionSet:
        return PermissionSet(self._permissions & other._permissions)

    def as_set(self) -> set[str]:
        return set(self._permissions)


class PermissionHierarchy:
    def __init__(self) -> None:
        self._actor_permissions: dict[str, set[str]] = {}
        self._inheritance: dict[str, set[str]] = {}
        self._lock = threading.RLock()
        self._logger = get_logger(__name__)

    def grant(self, actor: str, permission: str) -> None:
        with self._lock:
            self._actor_permissions.setdefault(actor, set()).add(permission)
            self._logger.info(f"Granted permission '{permission}' to actor '{actor}'")

    def revoke(self, actor: str, permission: str) -> None:
        with self._lock:
            if actor in self._actor_permissions:
                self._actor_permissions[actor].discard(permission)

    def has(self, actor: str, permission: str) -> bool:
        with self._lock:
            return permission in self.effective_permissions(actor)

    def effective_permissions(self, actor: str) -> set[str]:
        with self._lock:
            perms = set(self._actor_permissions.get(actor, []))
            expanded: set[str] = set()
            for p in perms:
                expanded.add(p)
                expanded.update(self._resolve_inheritance(p))
            return expanded

    def _resolve_inheritance(self, permission: str, visited: set[str] | None = None) -> set[str]:
        if visited is None:
            visited = set()
        if permission in visited:
            return set()
        visited.add(permission)
        result: set[str] = set()
        for inherited in self._inheritance.get(permission, []):
            result.add(inherited)
            result.update(self._resolve_inheritance(inherited, visited))
        return result
