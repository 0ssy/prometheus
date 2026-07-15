"""P8 Cloud Platform — tenant RBAC, isolation, billing metering."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import core.database as cd
from enterprise.cloud import AuthService, BillingService
from enterprise.models import Tenant, Role, User, UsageEvent, Invoice


@pytest.fixture
def session(tmp_path, monkeypatch):
    db_path = tmp_path / "p8.db"
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(cd, "engine", engine)
    monkeypatch.setattr(cd, "SessionLocal", factory)
    cd.init_db()
    with factory() as s:
        yield s
    engine.dispose()


def _setup(session):
    auth = AuthService(session)
    t_a = auth.create_tenant("Acme")
    t_b = auth.create_tenant("OtherCo")
    role_a = auth.create_role(t_a.id, "admin", ["device.read", "device.write"])
    role_b = auth.create_role(t_b.id, "viewer", ["device.read"])
    u_a = auth.create_user(t_a.id, role_a.id, "a@acme")
    u_b = auth.create_user(t_b.id, role_b.id, "b@other")
    return t_a, t_b, u_a, u_b


def test_rbac_allows_granted_action(session):
    t_a, t_b, u_a, u_b = _setup(session)
    auth = AuthService(session)
    assert auth.authorize(u_a.id, "device.write") is True
    assert auth.authorize(u_b.id, "device.write") is False


def test_tenant_boundary_blocks_cross_tenant(session):
    t_a, t_b, u_a, u_b = _setup(session)
    auth = AuthService(session)
    assert auth.can_access_tenant(u_a.id, t_a.id) is True
    assert auth.can_access_tenant(u_a.id, t_b.id) is False


def test_inactive_user_denied(session):
    t_a, t_b, u_a, u_b = _setup(session)
    auth = AuthService(session)
    session.get(User, u_a.id).active = False
    session.commit()
    assert auth.authorize(u_a.id, "device.read") is False


def test_billing_invoice_and_discrepancy(session):
    t_a, t_b, u_a, u_b = _setup(session)
    bill = BillingService(session)
    bill.record_usage(t_a.id, "tokens", 1000, 0.001)
    bill.record_usage(t_a.id, "tokens", 500, 0.001)
    inv = bill.generate_invoice(t_a.id, "2026-07")
    assert inv.total == pytest.approx(1.5)
    assert bill.discrepancy(inv) == pytest.approx(0.0)


def test_tenant_isolation_in_billing(session):
    t_a, t_b, u_a, u_b = _setup(session)
    bill = BillingService(session)
    bill.record_usage(t_a.id, "tokens", 100, 0.01)
    bill.record_usage(t_b.id, "tokens", 999, 0.01)
    inv_a = bill.generate_invoice(t_a.id, "2026-07")
    assert inv_a.total == pytest.approx(1.0)
