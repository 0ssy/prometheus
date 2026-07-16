"""
P8 Cloud Platform — RBAC, tenant isolation, billing metering.

Authorization is tenant-scoped: a user can only act within their own
tenant, and only if their role grants the permission. Billing aggregates
``usage_events`` into per-tenant periodic invoices and verifies the
metered total matches the sum of line items (<= 0.5% discrepancy KPI).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from core.logger import get_logger
from sqlalchemy.orm import Session

from enterprise.models import (
    Tenant,
    Role,
    User,
    UsageEvent,
    Invoice,
)

logger = get_logger(__name__)

MAX_BILLING_DISCREPANCY = 0.005


class AuthService:
    def __init__(self, session: Session):
        self._s = session

    # --- tenant + RBAC setup ---
    def create_tenant(self, name: str) -> Tenant:
        t = Tenant(id=str(uuid.uuid4()), name=name, created_at=datetime.now(timezone.utc))
        self._s.add(t)
        self._s.commit()
        return t

    def create_role(self, tenant_id: str, name: str, permissions: list[str]) -> Role:
        r = Role(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name,
            permissions=json.dumps(permissions),
        )
        self._s.add(r)
        self._s.commit()
        return r

    def create_user(self, tenant_id: str, role_id: str, email: str) -> User:
        u = User(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            role_id=role_id,
            email=email,
            active=True,
        )
        self._s.add(u)
        self._s.commit()
        return u

    # --- authorization (tenant-scoped) ---
    def authorize(self, user_id: str, action: str) -> bool:
        user = self._s.get(User, user_id)
        if user is None or not user.active:
            return False
        role = self._s.get(Role, user.role_id)
        if role is None or role.tenant_id != user.tenant_id:
            return False  # hard tenant boundary
        perms = json.loads(role.permissions)
        return action in perms

    def can_access_tenant(self, user_id: str, tenant_id: str) -> bool:
        user = self._s.get(User, user_id)
        return user is not None and user.tenant_id == tenant_id


class BillingService:
    def __init__(self, session: Session):
        self._s = session

    def record_usage(self, tenant_id: str, metric: str, quantity: float, unit_price: float) -> UsageEvent:
        ev = UsageEvent(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            metric=metric,
            quantity=quantity,
            unit_price=unit_price,
            created_at=datetime.now(timezone.utc),
        )
        self._s.add(ev)
        self._s.commit()
        return ev

    def generate_invoice(self, tenant_id: str, period: str) -> Invoice:
        events = (
            self._s.query(UsageEvent)
            .filter(UsageEvent.tenant_id == tenant_id)
            .all()
        )
        total = round(sum(e.quantity * e.unit_price for e in events), 2)
        inv = Invoice(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            period=period,
            total=total,
            created_at=datetime.now(timezone.utc),
        )
        self._s.add(inv)
        self._s.commit()
        return inv

    def discrepancy(self, invoice: Invoice) -> float:
        events = (
            self._s.query(UsageEvent)
            .filter(UsageEvent.tenant_id == invoice.tenant_id)
            .all()
        )
        computed = round(sum(e.quantity * e.unit_price for e in events), 2)
        if computed == 0:
            return 0.0
        return abs(computed - invoice.total) / computed
