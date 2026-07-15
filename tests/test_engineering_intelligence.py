"""P4 Engineering Intelligence — confidence gating, approval, feedback metrics."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import core.database as cd
from engineering.intelligence import EngineeringIntelligence, Suggestion
from engineering.models import EngineeringReport, EngineeringFeedback


@pytest.fixture
def session(tmp_path, monkeypatch):
    db_path = tmp_path / "p4.db"
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


def test_low_confidence_not_displayed(session):
    ei = EngineeringIntelligence(confidence_threshold=0.6)
    rep = ei.submit(session, Suggestion("fix", "maybe", confidence=0.3))
    assert rep.status == "pending"
    # Below threshold cannot be approved.
    with pytest.raises(PermissionError):
        ei.approve(session, rep.id)


def test_high_confidence_displayed_and_approved(session):
    ei = EngineeringIntelligence(confidence_threshold=0.6)
    rep = ei.submit(session, Suggestion("refactor", "safe", confidence=0.9))
    assert rep.status == "displayed"
    approved = ei.approve(session, rep.id)
    assert approved.approved is True
    assert approved.status == "executed"


def test_feedback_metrics(session):
    ei = EngineeringIntelligence()
    r1 = ei.submit(session, Suggestion("a", "x", 0.9))
    r2 = ei.submit(session, Suggestion("b", "y", 0.9))
    ei.record_feedback(session, r1.id, accepted=True, false_positive=False)
    ei.record_feedback(session, r2.id, accepted=False, false_positive=True)
    m = ei.metrics(session)
    assert m["acceptance_rate"] == pytest.approx(0.5)
    assert m["false_positive_rate"] == pytest.approx(0.5)
    assert m["sample_size"] == 2


def test_reject_sets_status(session):
    ei = EngineeringIntelligence()
    rep = ei.submit(session, Suggestion("c", "z", 0.9))
    ei.reject(session, rep.id)
    row = session.get(EngineeringReport, rep.id)
    assert row.status == "rejected"
