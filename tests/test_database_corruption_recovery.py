import os
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import core.database as cd
from core.database import init_db


def test_init_db_recovers_from_corruption(tmp_path):
    db_path = tmp_path / "prometheus.db"

    # Create a file with garbage bytes (valid size, invalid header).
    with open(db_path, "wb") as fh:
        fh.write(b"this is not a valid sqlite database file at all")

    # Point the module-level engine at the corrupted file.
    engine = create_engine(f"sqlite:///{db_path}")
    original_engine = cd.engine
    original_session_local = cd.SessionLocal
    cd.engine = engine
    cd.SessionLocal = sessionmaker(bind=engine)

    try:
        # Must not raise.
        init_db()

        # Fresh schema now exists (engine recreated the file).
        assert db_path.exists()
        assert os.path.getsize(db_path) >= 0
        conn = sqlite3.connect(str(db_path))
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        conn.close()
        assert "knowledge_nodes" in tables
        assert "knowledge_edges" in tables

        # Corrupt file was quarantined.
        corrupt = list(tmp_path.glob("prometheus.db.corrupted.*"))
        assert len(corrupt) == 1
        with open(corrupt[0], "rb") as fh:
            assert fh.read() == b"this is not a valid sqlite database file at all"
    finally:
        cd.engine = original_engine
        cd.SessionLocal = original_session_local


def test_corrupted_db_recovers_through_running_server(tmp_path, monkeypatch):
    """A pre-existing corrupt DB must not block a real boot (integration).

    Mirrors the user-facing scenario: a stale/corrupt ``prometheus.db`` on
    disk, then the platform boots and serves ``/health`` while the bad file
    is quarantined and a fresh schema is recreated. Exercises the recovery
    path through the running ASGI app rather than ``init_db`` directly.
    """
    import core.config as cc
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_path = tmp_path / "prometheus.db"
    with open(db_path, "wb") as fh:
        fh.write(b"this is not a valid sqlite database file at all")

    monkeypatch.setattr(cc.config, "db_path", str(db_path))
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(cd, "engine", engine)
    monkeypatch.setattr(
        cd, "SessionLocal", sessionmaker(autocommit=False, autoflush=False, bind=engine)
    )

    import backend.main as main_module
    from fastapi.testclient import TestClient

    with TestClient(main_module.app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json().get("status") == "ok"

    # Corrupt file was quarantined and a fresh DB recreated.
    assert any(
        p.name.startswith("prometheus.db.corrupted.") for p in tmp_path.iterdir()
    )
    assert db_path.exists()
