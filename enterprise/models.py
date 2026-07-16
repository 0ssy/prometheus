"""
P8 Cloud Platform — persistence models.

Multi-tenant platform with strict isolation: every row is scoped by
``tenant_id``. RBAC is modeled as Tenant -> User -> Role -> Permission.
Billing is metered via ``usage_events`` and aggregated into ``invoices``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text, Float, Boolean

from core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Role(Base):
    __tablename__ = "roles"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    permissions = Column(Text, default="[]")  # JSON list of permission strings


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, index=True, nullable=False)
    role_id = Column(String, index=True, nullable=False)
    email = Column(String, nullable=False)
    active = Column(Boolean, default=True, nullable=False)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, index=True, nullable=False)
    metric = Column(String, nullable=False)
    quantity = Column(Float, default=0.0, nullable=False)
    unit_price = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, index=True, nullable=False)
    period = Column(String, nullable=False)  # e.g. 2026-07
    total = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
