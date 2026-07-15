"""P9 Prometheus SDK — versioning + compatibility matrix."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import core.database as cd
from sdk.registry import SdkRegistry, is_compatible, PublishedSdk
from sdk.models import SdkVersion


@pytest.fixture
def session(tmp_path, monkeypatch):
    db_path = tmp_path / "p9.db"
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


def test_compatibility_matrix_semver():
    # major mismatch -> incompatible
    assert is_compatible("1.0.0", "2.0.0") is False
    # same major, additive minor -> compatible
    assert is_compatible("1.0.0", "1.1.0") is True
    # patch differences compatible
    assert is_compatible("1.1.0", "1.1.3") is True
    # reverse: higher minor is not "compatible target" for lower
    assert is_compatible("1.2.0", "1.1.0") is False


def test_publish_and_list_per_language(session):
    reg = SdkRegistry()
    reg.publish(session, PublishedSdk(
        "rust", "1.0.0", "1.0.0"))
    reg.publish(session, PublishedSdk(
        "rust", "1.1.0", "1.0.0"))
    reg.publish(session, PublishedSdk(
        "python", "0.9.0", "0.9.0"))
    rust = reg.list_for_language(session, "rust")
    assert len(rust) == 2
    py = reg.list_for_language(session, "python")
    assert len(py) == 1


def test_compatible_versions_query(session):
    reg = SdkRegistry()
    Sdk = PublishedSdk
    reg.publish(session, Sdk("rust", "1.0.0", "1.0.0"))
    reg.publish(session, Sdk("rust", "2.0.0", "2.0.0"))
    # Querying compatibility against 1.5.0 should match the 1.x line only.
    compat = reg.compatible(session, "rust", "1.5.0")
    names = {v.version for v in compat}
    assert "1.0.0" in names
    assert "2.0.0" not in names
