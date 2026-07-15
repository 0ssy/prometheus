"""P5 Titan AI Platform — license governance + reproducibility."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import core.database as cd
from titan.governance import TitanGovernance, LicenseError, scan_license
from titan.models import Dataset, Model


@pytest.fixture
def session(tmp_path, monkeypatch):
    db_path = tmp_path / "p5.db"
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


def test_approved_license_accepted(session):
    g = TitanGovernance()
    ds = g.register_dataset(session, "corpus", "MIT", "raw text")
    assert ds.license == "mit"
    rows = session.query(Dataset).all()
    assert len(rows) == 1


def test_unapproved_license_blocked(session):
    g = TitanGovernance()
    with pytest.raises(LicenseError, match="Unapproved"):
        g.register_dataset(session, "corpus", "GPL-3.0", "raw text")
    assert session.query(Dataset).count() == 0


def test_scan_license_case_insensitive():
    assert scan_license("Apache-2.0") is True
    assert scan_license("proprietary") is False


def test_reproducibility_hash_roundtrip(session):
    g = TitanGovernance()
    ds = g.register_dataset(session, "corpus", "MIT", "raw text")
    model = g.register_model(
        session, "m", "1.0", ds.id,
        eval_scores={"accuracy": 0.9},
        artifact_path="/models/m.bin",
        dataset_hash=ds.source_hash, code_hash="abc", config={"lr": 1e-4},
    )
    assert g.verify_reproducibility(
        session, model.id, ds.source_hash, "abc", {"lr": 1e-4}
    ) is True
    assert g.verify_reproducibility(
        session, model.id, ds.source_hash, "DIFFERENT", {"lr": 1e-4}
    ) is False
