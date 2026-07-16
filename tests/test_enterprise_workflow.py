"""P11 Prometheus OS — end-to-end enterprise workflow integration."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import core.database as cd
from core.enterprise_workflow_runner import EnterpriseWorkflowRunner
from core.enterprise_workflow import EnterpriseWorkflow


@pytest.fixture
def session(tmp_path, monkeypatch):
    db_path = tmp_path / "p11.db"
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


def test_e2e_workflow_records_success(session):
    runner = EnterpriseWorkflowRunner()
    res = runner.run(session, "firmware-recovery", "dev-1")
    assert res.success is True
    assert len(res.steps) == 5
    assert all(s["ok"] for s in res.steps)
    row = session.query(EnterpriseWorkflow).one()
    assert row.success is True
    assert row.device_id == "dev-1"


def test_e2e_workflow_isolates_step_failure(session):
    runner = EnterpriseWorkflowRunner()
    # Override the deploy step so it raises, proving the run is isolated.
    runner._deploy = lambda device_id: (_ for _ in ()).throw(RuntimeError("deploy failed"))
    res = runner.run(session, "firmware-recovery", "dev-2")
    assert res.success is False
    row = session.query(EnterpriseWorkflow).one()
    assert row.success is False


def test_success_rate(session):
    runner = EnterpriseWorkflowRunner()
    runner.run(session, "w", "dev-1")
    runner.run(session, "w", "dev-2")
    assert runner.success_rate(session) == pytest.approx(1.0)
