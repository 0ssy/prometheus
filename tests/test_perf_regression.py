"""P6 High Performance Engine — perf recording + regression guard."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import core.database as cd
from benchmarks.regression import PerfRegistry, PerfRun
from benchmarks.perf_models import PerfMetric


@pytest.fixture
def session(tmp_path, monkeypatch):
    db_path = tmp_path / "p6.db"
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


def test_record_persists_metric(session):
    reg = PerfRegistry()
    metric = reg.record(session, PerfRun("r1", "tier-a", 120.0, 50.0, 0.8))
    assert session.query(PerfMetric).count() == 1
    assert metric.tokens_per_sec == 120.0


def test_no_regression_within_threshold(session):
    reg = PerfRegistry(max_regression=0.03)
    reg.record(session, PerfRun("r1", "tier-a", 100.0))
    m2 = reg.record(session, PerfRun("r2", "tier-a", 99.0))  # -1% within 3%
    result = reg.check_regression(session, m2)
    assert result["regression"] is False


def test_regression_beyond_threshold_fails(session):
    reg = PerfRegistry(max_regression=0.03)
    reg.record(session, PerfRun("r1", "tier-a", 100.0))
    m2 = reg.record(session, PerfRun("r2", "tier-a", 90.0))  # -10% > 3%
    result = reg.check_regression(session, m2)
    assert result["regression"] is True
    assert result["delta"] == pytest.approx(-0.10, abs=1e-3)


def test_first_run_has_no_baseline(session):
    reg = PerfRegistry()
    m = reg.record(session, PerfRun("r1", "tier-a", 100.0))
    result = reg.check_regression(session, m)
    assert result["regression"] is False
    assert result["previous"] is None
