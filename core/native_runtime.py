"""
Native runtime manager for non-Python services (Go/Rust/C++).

Starts/stops the Go control-plane and billing processes when available so
Python remains the orchestrator while native services run as isolated
process boundaries.
"""

from __future__ import annotations

import os
import json
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from core.config import config
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class _ServiceSpec:
    name: str
    command: list[str]
    cwd: Path
    health_url: str
    required_tool: str


class NativeRuntimeManager:
    def __init__(self, mode: str | None = None):
        self._mode = (mode or config.native_runtime_mode).strip().lower()
        self._processes: dict[str, subprocess.Popen] = {}
        self._status: dict[str, dict] = {}
        repo_root = Path(__file__).resolve().parent.parent
        self._services = [
            _ServiceSpec(
                name="go_controlplane",
                command=["go", "run", "./cmd/controlplane"],
                cwd=repo_root / "go",
                health_url=f"{config.go_controlplane_url.rstrip('/')}/health",
                required_tool="go",
            ),
            _ServiceSpec(
                name="go_billing",
                command=["go", "run", "./cmd/billing"],
                cwd=repo_root / "go",
                health_url=f"{config.go_billing_url.rstrip('/')}/health",
                required_tool="go",
            ),
        ]

    def start(self) -> None:
        if self._mode not in {"off", "auto", "on"}:
            raise ValueError(
                f"Invalid PROMETHEUS_NATIVE_RUNTIME='{self._mode}', expected off|auto|on"
            )

        if self._mode == "off":
            self._status = {
                spec.name: {"state": "disabled", "reason": "mode=off"}
                for spec in self._services
            }
            return

        # Keep unit/integration tests deterministic; test suites exercise
        # fallback paths and should not depend on host toolchains.
        if self._mode == "auto" and os.environ.get("PYTEST_CURRENT_TEST"):
            self._status = {
                spec.name: {"state": "disabled", "reason": "pytest auto-skip"}
                for spec in self._services
            }
            return

        for spec in self._services:
            self._start_service(spec)

    def stop(self) -> None:
        for name, proc in list(self._processes.items()):
            if proc.poll() is not None:
                continue
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
            self._status[name] = {"state": "stopped"}
        self._processes.clear()

    def status(self) -> dict:
        services: dict[str, dict] = {}
        for spec in self._services:
            record = dict(self._status.get(spec.name, {"state": "unknown"}))
            proc = self._processes.get(spec.name)
            if proc is not None:
                record["pid"] = proc.pid
                record["healthy"] = self._wait_for_health(
                    spec.health_url, timeout_seconds=0.3
                )
            else:
                record.setdefault("healthy", self._wait_for_health(spec.health_url, 0.3))
            record["health_url"] = spec.health_url
            services[spec.name] = record
        return {"mode": self._mode, "services": services}

    def _start_service(self, spec: _ServiceSpec) -> None:
        if shutil.which(spec.required_tool) is None:
            self._status[spec.name] = {
                "state": "missing_toolchain",
                "tool": spec.required_tool,
            }
            return

        if self._wait_for_health(spec.health_url, timeout_seconds=0.3):
            self._status[spec.name] = {"state": "external", "healthy": True}
            return

        try:
            proc = subprocess.Popen(
                spec.command,
                cwd=str(spec.cwd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            self._status[spec.name] = {"state": "failed_start", "error": str(exc)}
            return

        if not self._wait_for_health(
            spec.health_url,
            timeout_seconds=config.native_runtime_health_timeout_seconds,
        ):
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
            self._status[spec.name] = {"state": "failed_healthcheck"}
            return

        self._processes[spec.name] = proc
        self._status[spec.name] = {"state": "managed_running"}
        logger.info("Native service started: %s (pid=%s)", spec.name, proc.pid)

    @staticmethod
    def _wait_for_health(url: str, timeout_seconds: float) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            req = urllib.request.Request(url, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=0.7) as resp:
                    if 200 <= resp.status < 300:
                        return True
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
        return False


def create_http_cluster_submit(control_plane_url: str, timeout_seconds: float = 1.5):
    """
    Build a control-plane submit function for DistributedScheduler.

    Raises ``ClusterUnavailable`` on connection/response failures.
    """

    from distributed.scheduler import ClusterUnavailable

    base = control_plane_url.rstrip("/")

    def _submit(payload: dict) -> str:
        body = {
            "payload": str(payload),
            "status": "queued",
        }
        req = urllib.request.Request(
            f"{base}/tasks",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                if resp.status not in (200, 201):
                    raise ClusterUnavailable(
                        f"control plane returned unexpected status {resp.status}"
                    )
                data = json.loads(resp.read().decode("utf-8") or "{}")
                return str(data.get("id", "remote-task"))
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ClusterUnavailable(f"control plane unreachable: {exc}") from exc

    return _submit
