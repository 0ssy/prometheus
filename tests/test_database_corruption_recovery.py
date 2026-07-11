import os
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import core.database as cd
from core.database import Base, init_db


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
