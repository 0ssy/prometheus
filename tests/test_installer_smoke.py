"""
Installer smoke test.

Validates the end-to-end install path that a new user hits:
  pip install -r requirements.txt
  python prometheus.py --server   (or `prometheus` console script)
  -> platform boots, /health + /status + /docs respond

This guards against missing dependencies (e.g. TestClient's httpx) and
regressions in the boot sequence that would block a clean install from
ever coming online.
"""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _point_db_at(tmp_path, monkeypatch):
    """Redirect the process-wide DB engine at an isolated path.

    config.db_path and the engine are resolved at import time, so a clean
    install must be simulated by repointing them before boot.
    """
    import core.config as cc
    import core.database as cd

    db_path = tmp_path / "installer_smoke.db"
    monkeypatch.setattr(cc.config, "db_path", str(db_path))
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(cd, "engine", engine)
    monkeypatch.setattr(
        cd, "SessionLocal", sessionmaker(autocommit=False, autoflush=False, bind=engine)
    )
    return db_path


def test_installed_platform_boots_and_serves(tmp_path, monkeypatch):
    db_path = _point_db_at(tmp_path, monkeypatch)

    import backend.main as main_module
    from fastapi.testclient import TestClient

    with TestClient(main_module.app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json().get("status") == "ok"

        assert client.get("/status").status_code == 200
        # Interactive API docs must be reachable after a clean install.
        assert client.get("/docs").status_code == 200

    # Boot should have created a fresh database file on disk.
    assert db_path.exists()


def test_corrupted_db_still_boots_after_install(tmp_path, monkeypatch):
    """A clean install must survive a pre-existing corrupt DB (Task 3)."""
    db_path = _point_db_at(tmp_path, monkeypatch)
    with open(db_path, "wb") as fh:
        fh.write(b"not a real sqlite database")

    import backend.main as main_module
    from fastapi.testclient import TestClient

    with TestClient(main_module.app) as client:
        assert client.get("/health").status_code == 200

    # Corrupt file was quarantined and a fresh schema recreated.
    assert any(
        p.name.startswith("installer_smoke.db.corrupted.") for p in tmp_path.iterdir()
    )
    assert db_path.exists()
