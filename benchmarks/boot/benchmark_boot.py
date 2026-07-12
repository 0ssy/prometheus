"""Boot benchmark: measure time from server start to first /health 200.

Mirrors the boot gate in `.github/workflows/performance.yml`. Start the
platform with ``prometheus.py --server`` and time how long until the
``/health`` endpoint returns a 200.

Run from the repository root:

    python benchmarks/boot/benchmark_boot.py

Environment overrides:

    MAX_BOOT_SECONDS=5.0   # fail if boot exceeds this
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psutil

ROOT = Path(__file__).resolve().parent.parent.parent
MAX_BOOT_SECONDS = float(os.environ.get("MAX_BOOT_SECONDS", "5.0"))


def _terminate_tree(proc: subprocess.Popen) -> None:
    """Terminate the server and any child workers it forked."""
    try:
        parent = psutil.Process(proc.pid)
        children = parent.children(recursive=True)
    except psutil.NoSuchProcess:
        children = []
    if proc.poll() is None:
        proc.terminate()
    for child in children:
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        for child in children:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass


def _wait_for_health(client: httpx.Client, attempts: int = 120) -> float:
    """Poll /health and return seconds until first 200."""
    start = time.perf_counter()
    for _ in range(attempts):
        try:
            r = client.get("http://127.0.0.1:8000/health")
            if r.status_code == 200:
                return time.perf_counter() - start
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError("Server did not reach /health in time")


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, "prometheus.py", "--server"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    client = httpx.Client(timeout=2.0)
    try:
        boot_seconds = _wait_for_health(client)
        metrics = {"boot_seconds": round(boot_seconds, 3)}
        print(json.dumps(metrics, indent=2))
        if boot_seconds > MAX_BOOT_SECONDS:
            raise RuntimeError(
                f"boot time regression: {boot_seconds}s > {MAX_BOOT_SECONDS}s"
            )
    finally:
        client.close()
        _terminate_tree(proc)
    print("BOOT OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
