"""
Prometheus Task Scheduler
-----------------------------------------
Minimal in-process scheduler using a background thread. This is
intentionally not Celery/APScheduler-grade infrastructure — Phase
Alpha just needs to prove Prometheus can run something on a timer
without blocking the API. Swap this for something more serious
once you actually have jobs that need retries, persistence, or
distributed workers.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from contracts.scheduler import SchedulerApi
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class JobRecord:
    name: str
    func: Callable[[], None]
    interval_seconds: int
    status: str = "scheduled"
    last_run: float | None = None
    next_run: float = 0.0
    failures: int = 0
    retries: int = 0
    max_retries: int = 3
    last_error: str | None = None


class TaskScheduler(SchedulerApi):
    def __init__(self):
        self._jobs: list[JobRecord] = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def schedule(self, name: str, func: Callable[[], None], interval_seconds: int) -> None:
        with self._lock:
            existing = next((j for j in self._jobs if j.name == name), None)
            if existing is not None:
                existing.interval_seconds = interval_seconds
                existing.func = func
                return
            record = JobRecord(name=name, func=func, interval_seconds=interval_seconds, next_run=time.time() + interval_seconds)
            self._jobs.append(record)
        logger.info(f"Scheduled job '{name}' every {interval_seconds}s")

    def _run_loop(self):
        while not self._stop_event.is_set():
            now = time.time()
            with self._lock:
                for job in self._jobs:
                    if job.status == "paused":
                        continue
                    if now >= job.next_run:
                        try:
                            job.func()
                            job.status = "completed"
                            job.last_run = now
                            job.next_run = now + job.interval_seconds
                            job.failures = 0
                            job.retries = 0
                            job.last_error = None
                        except Exception as exc:
                            job.failures += 1
                            job.last_error = str(exc)
                            logger.exception(f"Scheduled job '{job.name}' raised an exception")
                            if job.retries < job.max_retries:
                                job.retries += 1
                                job.status = "running"
                                job.next_run = now + (2 ** job.retries)
                            else:
                                job.status = "failed"
            self._stop_event.wait(1)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self):
        self._stop_event.set()

    def list_jobs(self) -> list[str]:
        with self._lock:
            return [job.name for job in self._jobs]

    def jobs_detail(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "name": job.name,
                    "interval_seconds": job.interval_seconds,
                    "status": job.status,
                    "last_run": job.last_run,
                    "next_run": job.next_run,
                    "failures": job.failures,
                    "retries": job.retries,
                    "max_retries": job.max_retries,
                    "last_error": job.last_error,
                }
                for job in self._jobs
            ]

    def pause(self, name: str) -> None:
        with self._lock:
            job = next((j for j in self._jobs if j.name == name), None)
            if job is not None:
                job.status = "paused"

    def resume(self, name: str) -> None:
        with self._lock:
            job = next((j for j in self._jobs if j.name == name), None)
            if job is not None and job.status == "paused":
                job.status = "scheduled"
                job.next_run = time.time()

    def trigger(self, name: str) -> None:
        with self._lock:
            job = next((j for j in self._jobs if j.name == name), None)
            if job is not None:
                try:
                    job.func()
                    job.status = "completed"
                    job.last_run = time.time()
                    job.next_run = time.time() + job.interval_seconds
                    job.failures = 0
                    job.retries = 0
                    job.last_error = None
                except Exception as exc:
                    job.failures += 1
                    job.last_error = str(exc)
                    job.status = "failed"
                    logger.exception(f"Triggered job '{job.name}' raised an exception")


scheduler = TaskScheduler()
