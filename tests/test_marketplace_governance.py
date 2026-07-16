"""P10 Engineering Ecosystem — marketplace governance workflow."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import core.database as cd
from marketplace.governance import MarketplaceGovernance, Submission
from marketplace.models import MarketplaceApproval


@pytest.fixture
def session(tmp_path, monkeypatch):
    db_path = tmp_path / "p10.db"
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


def test_submit_then_review_approved(session):
    g = MarketplaceGovernance(quality_gate=0.7)
    sub = g.submit(session, Submission("s1", "Firmware Tool", "tooling", "alice"))
    assert sub.status == "pending"
    reviewed = g.review(session, sub.id, "approved", "reviewer-1", 0.9, "looks good")
    assert reviewed.status == "approved"
    assert reviewed.quality_score == 0.9


def test_quality_gate_blocks_low_score(session):
    g = MarketplaceGovernance(quality_gate=0.7)
    sub = g.submit(session, Submission("s2", "Sketchy", "tooling", "bob"))
    with pytest.raises(PermissionError):
        g.review(session, sub.id, "approved", "reviewer-1", 0.4)
    # But rejection is allowed.
    g.review(session, sub.id, "rejected", "reviewer-1", 0.4, "low quality")
    assert session.get(MarketplaceApproval, sub.id).status == "rejected"


def test_review_twice_rejected(session):
    g = MarketplaceGovernance()
    sub = g.submit(session, Submission("s3", "Tool", "tooling", "carol"))
    g.review(session, sub.id, "approved", "r", 0.9)
    with pytest.raises(ValueError, match="already reviewed"):
        g.review(session, sub.id, "rejected", "r", 0.9)


def test_approval_rate(session):
    g = MarketplaceGovernance(quality_gate=0.7)
    a = g.submit(session, Submission("s4", "A", "tooling", "x"))
    b = g.submit(session, Submission("s5", "B", "tooling", "y"))
    g.review(session, a.id, "approved", "r", 0.9)
    g.review(session, b.id, "rejected", "r", 0.5)
    assert g.approval_rate(session) == pytest.approx(0.5)
