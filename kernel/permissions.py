from __future__ import annotations


class PermissionManager:
    def __init__(self):
        self._grants: dict[str, set[str]] = {}

    def grant(self, actor: str, permission: str) -> None:
        self._grants.setdefault(actor, set()).add(permission)

    def revoke(self, actor: str, permission: str) -> None:
        if actor in self._grants:
            self._grants[actor].discard(permission)

    def permissions_for(self, actor: str) -> set[str]:
        return set(self._grants.get(actor, set()))

    def check(self, actor: str, required: set[str]) -> bool:
        return required.issubset(self.permissions_for(actor))
