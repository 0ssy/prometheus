from unittest.mock import patch

import pytest

from core.scheduler import TaskScheduler


def test_schedule_and_list_jobs():
    scheduler = TaskScheduler()
    scheduler.schedule("ping", lambda: None, interval_seconds=10)
    assert "ping" in scheduler.list_jobs()


def test_pause_resume_trigger():
    scheduler = TaskScheduler()
    scheduler.schedule("job1", lambda: None, interval_seconds=5)
    scheduler.pause("job1")
    detail = scheduler.jobs_detail()[0]
    assert detail["status"] == "paused"
    scheduler.resume("job1")
    detail = scheduler.jobs_detail()[0]
    assert detail["status"] == "scheduled"
    scheduler.trigger("job1")
    detail = scheduler.jobs_detail()[0]
    assert detail["status"] == "completed"


def test_failure_retry_then_failed():
    scheduler = TaskScheduler()
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("boom")

    scheduler.schedule("flaky", flaky, interval_seconds=1)
    scheduler.trigger("flaky")
    detail = scheduler.jobs_detail()[0]
    assert detail["failures"] == 1
    assert detail["status"] == "failed"


def test_jobs_detail_shape():
    scheduler = TaskScheduler()
    scheduler.schedule("a", lambda: None, interval_seconds=1)
    scheduler.schedule("b", lambda: None, interval_seconds=2)
    details = scheduler.jobs_detail()
    assert len(details) == 2
    for d in details:
        assert "name" in d
        assert "status" in d
        assert "failures" in d
        assert "next_run" in d
