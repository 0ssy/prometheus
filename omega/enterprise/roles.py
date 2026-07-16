from __future__ import annotations

from dataclasses import dataclass, field
import threading
import uuid

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Role:
    role_id: str
    org_id: str
    name: str
    permissions: set[str] = field(default_factory=set)
    inherits: list[str] = field(default_factory=list)


class RoleRegistry:
    def __init__(self) -> None:
        self._roles: dict[str, Role] = {}
        self._lock = threading.RLock()

    def create(self, org_id: str, name: str, permissions: set[str] | None = None, inherits: list[str] | None = None) -> Role:
        role_id = str(uuid.uuid4())
        role = Role(role_id=role_id, org_id=org_id, name=name, permissions=permissions or set(), inherits=inherits or [])
        with self._lock:
            self._roles[role_id] = role
        return role

    def get(self, role_id: str) -> Role | None:
        with self._lock:
            return self._roles.get(role_id)

    def list_by_org(self, org_id: str) -> list[Role]:
        with self._lock:
            return [r for r in self._roles.values() if r.org_id == org_id]

    def add_permission(self, role_id: str, permission: str) -> None:
        with self._lock:
            role = self._roles.get(role_id)
            if role:
                role.permissions.add(permission)

    def remove_permission(self, role_id: str, permission: str) -> None:
        with self._lock:
            role = self._roles.get(role_id)
            if role:
                role.permissions.discard(permission)

    def get_effective_permissions(self, role_id: str) -> set[str]:
        with self._lock:
            role = self._roles.get(role_id)
            if role is None:
                return set()
            perms = set(role.permissions)
            for inherited_id in role.inherits:
                inherited = self._roles.get(inherited_id)
                if inherited:
                    perms.update(inherited.permissions)
            return perms
