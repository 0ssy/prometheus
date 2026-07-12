"""Memory benchmark: RSS after startup and after 100 API calls.

Mirrors the memory gate in `.github/workflows/performance.yml`. Starts the
platform with ``prometheus.py --server``, samples the process RSS once it is
healthy, then issues 100 API calls and samples again to confirm bounded
growth.

Run from the repository root:

    python benchmarks/memory/benchmark_memory.py

Environment overrides:

    MAX_MEMORY_MB=350        # fail if RSS after 100 calls exceeds this
    API_CALLS=100            # number of warm-up calls before the 2nd sample
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
MAX_MEMORY_MB = float(os.environ.get("MAX_MEMORY_MB", "350"))
API_CALLS = int(os.environ.get("API_CALLS", "100"))


def _wait_for_health(client: httpx.Client, attempts: int = 120) -> None:
    for _ in range(attempts):
        try:
            r = client.get("http://127.0.0.1:8000/health")
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError("Server did not reach /health in time")


def _rss_mb(pid: int) -> float:
    return psutil.Process(pid).memory_info().rss / (1024 * 1024)


def _tree_rss_mb(proc: "subprocess.Popen") -> float:
    """Sum RSS across the server process tree.

    ``prometheus.py --server`` forks a uvicorn worker, so the launcher
    process stays tiny while the actual work (and the memory we care about)
    lives in the child. We measure the whole tree to avoid an under-count.
    """
    total = _rss_mb(proc.pid)
    try:
        for child in psutil.Process(proc.pid).children(recursive=True):
            total += child.memory_info().rss
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return total / (1024 * 1024)


def _terminate_tree(proc: "subprocess.Popen") -> None:
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


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, "prometheus.py", "--server"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    client = httpx.Client(timeout=2.0)
    try:
        _wait_for_health(client)
        rss_after_boot = _tree_rss_mb(proc)

        for _ in range(API_CALLS):
            client.get("http://127.0.0.1:8000/health")
            client.get("http://127.0.0.1:8000/status")

        rss_after_calls = _tree_rss_mb(proc)

        metrics = {
            "memory_mb_after_boot": round(rss_after_boot, 2),
            "memory_mb_after_100_calls": round(rss_after_calls, 2),
            "api_calls": API_CALLS,
        }
        print(json.dumps(metrics, indent=2))
        if rss_after_calls > MAX_MEMORY_MB:
            raise RuntimeError(
                f"memory regression: {rss_after_calls} MB > {MAX_MEMORY_MB} MB"
            )
    finally:
        client.close()
        _terminate_tree(proc)
    print("MEMORY OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
