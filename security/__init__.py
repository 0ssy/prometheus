"""
Security package (Epsilon / Hephaestus phase)
---------------------------------------------
Security layer for hardware operations.

Everything here enforces the core invariant: nothing executes anonymously.
Every hardware action is authorized, auditable, and integrity-checked.
"""

from __future__ import annotations

from security.auditing import AuditEntry, AuditLogger
from security.authorization import AuthorizationResult, Authorizer
from security.integrity import AttestationResult, IntegrityCheck, IntegrityVerifier
from security.permissions import Permission, PermissionRegistry, default_registry

__all__ = [
    "AuthorizationResult",
    "Authorizer",
    "Permission",
    "PermissionRegistry",
    "default_registry",
    "AuditEntry",
    "AuditLogger",
    "IntegrityCheck",
    "IntegrityVerifier",
    "AttestationResult",
]
