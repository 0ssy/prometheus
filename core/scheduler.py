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
from typing import Callable
from core.logger import get_logger

logger = get_logger(__name__)


class TaskScheduler:
    def __init__(self):
        self._jobs: list[tuple[str, Callable, int]] = (
            []
        )  # (name, func, interval_seconds)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def schedule(self, name: str, func: Callable, interval_seconds: int) -> None:
        self._jobs.append((name, func, interval_seconds))
        logger.info(f"Scheduled job '{name}' every {interval_seconds}s")

    def _run_loop(self):
        last_run: dict[str, float] = {name: 0 for name, _, _ in self._jobs}
        while not self._stop_event.is_set():
            now = time.time()
            for name, func, interval in self._jobs:
                if now - last_run[name] >= interval:
                    try:
                        func()
                    except Exception:
                        logger.exception(f"Scheduled job '{name}' raised an exception")
                    last_run[name] = now
            self._stop_event.wait(1)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self):
        self._stop_event.set()


scheduler = TaskScheduler()
