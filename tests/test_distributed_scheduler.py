"""P7 Distributed Computing — scheduler client, fallback, recovery."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import core.database as cd
from core.native_runtime import create_http_cluster_submit
from distributed.scheduler import DistributedScheduler, ClusterUnavailable
from distributed.models import DistributedTask, DistributedRecovery


@pytest.fixture
def session(tmp_path, monkeypatch):
    db_path = tmp_path / "p7.db"
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


def test_submit_local_fallback_marks_done(session):
    sched = DistributedScheduler()
    task = sched.submit(session, {"op": "train"}, node_id="n1")
    assert task.status == "done"
    assert session.query(DistributedTask).count() == 1


def test_submit_to_cluster_marks_running(session):
    def cluster(payload):
        return "remote-id"

    sched = DistributedScheduler(cluster_submit=cluster)
    task = sched.submit(session, {"op": "eval"}, node_id="n2")
    assert task.status == "running"


def test_cluster_unavailable_falls_back(session):
    def cluster(payload):
        raise ClusterUnavailable("control plane down")

    sched = DistributedScheduler(cluster_submit=cluster)
    task = sched.submit(session, {"op": "x"})
    assert task.status == "done"  # local fallback succeeded


def test_recovery_requeues_task_and_logs(session):
    sched = DistributedScheduler()
    task = sched.submit(session, {"op": "x"})
    rec = sched.recover(session, task_id=task.id, node_id="n1", reason="node killed", recovered=True)
    assert rec.recovered == "true"
    assert session.get(DistributedTask, task.id).status == "queued"
    assert session.query(DistributedRecovery).count() == 1


def test_success_rate(session):
    sched = DistributedScheduler()
    sched.submit(session, {"op": "a"})
    sched.submit(session, {"op": "b"})
    assert sched.success_rate(session) == pytest.approx(1.0)


def test_http_cluster_submit_raises_when_control_plane_unreachable():
    submit = create_http_cluster_submit("http://127.0.0.1:9", timeout_seconds=0.1)
    with pytest.raises(ClusterUnavailable):
        submit({"op": "train"})
