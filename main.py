"""
Prometheus Platform Entry Point
-----------------------------------------
Bootstraps the platform runtime without binding it to any specific frontend.
FastAPI, CLI, and tests all share the same `boot()` path.
"""

from __future__ import annotations

import time

from core.bootstrap import boot, load_baseline
from core.container import ServiceContainer
from core.logger import get_logger

logger = get_logger(__name__)


def _heartbeat_job() -> None:
    logger.info("Prometheus heartbeat — platform runtime alive")


def run_platform() -> ServiceContainer:
    container = boot(_heartbeat_job)
    logger.info("Prometheus platform started")
    return container


def main() -> None:
    container = run_platform()
    scheduler = container.get("scheduler")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        scheduler.stop()
        logger.info("Prometheus platform stopped")


if __name__ == "__main__":
    main()
