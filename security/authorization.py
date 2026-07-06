"""
Security: Authorization (Epsilon / Hephaestus phase)
---------------------------------------------------
Checks whether an actor is authorized to perform a hardware action on a
resource. Nothing executes anonymously — every hardware operation must pass
through authorization first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable

from core.logger import get_logger
from security.permissions import PermissionRegistry, default_registry

logger = get_logger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AuthorizationResult:
    allowed: bool
    actor: str
    action: str
    resource: str
    reason: str
    timestamp: datetime = field(default_factory=_utc_now)


class Authorizer:
    def __init__(self, registry: PermissionRegistry | None = None):
        self._registry = registry or default_registry

    def authorize(
        self,
        actor: str,
        action: str,
        resource: str,
        permissions: set[str],
    ) -> AuthorizationResult:
        if not actor:
            return AuthorizationResult(
                allowed=False,
                actor=actor,
                action=action,
                resource=resource,
                reason="No actor identified — anonymous operations are forbidden",
            )

        if not action:
            return AuthorizationResult(
                allowed=False,
                actor=actor,
                action=action,
                resource=resource,
                reason="No action specified",
            )

        required = self._registry.required_for(action)

        missing = required - set(permissions)
        if missing:
            return AuthorizationResult(
                allowed=False,
                actor=actor,
                action=action,
                resource=resource,
                reason=f"Missing permissions: {sorted(missing)}",
            )

        for permission_name in required:
            permission = self._registry.get(permission_name)
            if permission is not None and permission.requires_ownership:
                if "ownership_declared" not in permissions:
                    return AuthorizationResult(
                        allowed=False,
                        actor=actor,
                        action=action,
                        resource=resource,
                        reason=(
                            f"Action '{action}' is ownership-gated but "
                            f"'ownership_declared' permission is absent"
                        ),
                    )

        logger.info(
            "Authorized actor=%s action=%s resource=%s", actor, action, resource
        )
        return AuthorizationResult(
            allowed=True,
            actor=actor,
            action=action,
            resource=resource,
            reason="Authorized",
        )

    def require_permission(self, permission: str) -> Callable:
        """Return a decorator that gates a callable behind a permission.

        The wrapped callable must accept `actor`, `action`, `resource`, and
        `permissions` among its keyword arguments (or be called with them).
        The decorator returns an AuthorizationResult instead of executing the
        wrapped function when authorization fails.
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                actor = kwargs.get("actor", "")
                action = kwargs.get("action", permission)
                resource = kwargs.get("resource", "")
                permissions: set[str] = kwargs.get("permissions", set())
                result = self.authorize(actor, action, resource, permissions)
                if not result.allowed:
                    logger.warning(
                        "Permission check failed for %s: %s", permission, result.reason
                    )
                    return result
                return func(*args, **kwargs)

            return wrapper

        return decorator
