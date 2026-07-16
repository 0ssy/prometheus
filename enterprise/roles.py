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
    permissions: set = field(default_factory=set)
    inherits: list = field(default_factory=list)


class RoleRegistry:
    def __init__(self) -> None:
        self._roles: dict[str, Role] = {}
        self._lock = threading.RLock()

    def create(
        self,
        org_id: str,
        name: str,
        permissions: set | None = None,
        inherits: list | None = None,
    ) -> Role:
        role = Role(
            role_id=f"role_{uuid.uuid4().hex[:12]}",
            org_id=org_id,
            name=name,
            permissions=set(permissions) if permissions else set(),
            inherits=list(inherits) if inherits else [],
        )
        with self._lock:
            self._roles[role.role_id] = role
        logger.info(f"Created role: {role.role_id} ({name})")
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
            if role is None:
                raise KeyError(f"Role not found: {role_id}")
            role.permissions.add(permission)
            logger.info(f"Added permission {permission!r} to role: {role_id}")

    def remove_permission(self, role_id: str, permission: str) -> None:
        with self._lock:
            role = self._roles.get(role_id)
            if role is None:
                raise KeyError(f"Role not found: {role_id}")
            role.permissions.discard(permission)
            logger.info(f"Removed permission {permission!r} from role: {role_id}")

    def get_effective_permissions(self, role_id: str) -> set[str]:
        with self._lock:
            role = self._roles.get(role_id)
            if role is None:
                raise KeyError(f"Role not found: {role_id}")
            effective: set[str] = set(role.permissions)
            for parent_id in role.inherits:
                parent = self._roles.get(parent_id)
                if parent is not None:
                    effective |= self.get_effective_permissions(parent_id)
            return effective
