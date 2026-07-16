from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import core.database as cd


def _point_db(tmp_path, monkeypatch):
    import core.config as cc

    db_path = tmp_path / "native_runtime_endpoints.db"
    monkeypatch.setattr(cc.config, "db_path", str(db_path))
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(cd, "engine", engine)
    monkeypatch.setattr(
        cd, "SessionLocal", sessionmaker(autocommit=False, autoflush=False, bind=engine)
    )


def test_native_runtime_endpoint_and_distributed_fallback(tmp_path, monkeypatch):
    _point_db(tmp_path, monkeypatch)

    import backend.main as main_module
    from fastapi.testclient import TestClient

    with TestClient(main_module.app) as client:
        native = client.get("/system/native-runtime")
        assert native.status_code == 200
        body = native.json()
        assert "mode" in body
        assert "services" in body

        submit = client.post("/distributed/tasks", json={"payload": {"op": "train"}})
        assert submit.status_code == 200
        assert submit.json()["status"] in ("done", "running")

        metrics = client.get("/distributed/metrics")
        assert metrics.status_code == 200
        assert "success_rate" in metrics.json()
