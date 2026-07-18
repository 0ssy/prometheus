"""Prometheus Platform 1.0 — one-command launcher.

Starts every subsystem in the correct order, waits for health checks,
and tears everything down cleanly on Ctrl+C.

Usage:
    python -m prometheus launch                      # full platform
    python -m prometheus launch --distributed        # + Go control plane + workers
    python -m prometheus launch --cloud              # + cloud gateway/auth/tunnel
    python -m prometheus launch --frontend           # + Vite dev server
    python -m prometheus launch --all                # everything above
    python -m prometheus launch --workers 4          # spawn N local workers
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

BACKEND_CMD = [sys.executable, "-m", "prometheus", "--server"]
FRONTEND_CMD = ["npm", "run", "dev", "--", "--host"]
GO_CONTROLPLANE_CMD = ["go", "run", "./cmd/controlplane"]
GO_WORKER_CMD = ["go", "run", "./cmd/worker"]
GO_BILLING_CMD = ["go", "run", "./cmd/billing"]
CLOUD_GATEWAY_CMD = ["go", "run", "./cmd/gateway"]
CLOUD_AUTH_CMD = ["go", "run", "./cmd/auth"]
CLOUD_TUNNEL_CMD = ["go", "run", "./cmd/tunnel"]

BACKEND_URL = "http://127.0.0.1:8000/health"
FRONTEND_URL = "http://localhost:5173"
GO_HEALTH_URL = "http://127.0.0.1:8080/health"
GO_BILLING_HEALTH_URL = "http://127.0.0.1:8081/health"
CLOUD_GATEWAY_HEALTH_URL = "http://127.0.0.1:8080/health"
CLOUD_AUTH_HEALTH_URL = "http://127.0.0.1:8081/health"
CLOUD_TUNNEL_HEALTH_URL = "http://127.0.0.1:8083/health"


class ComponentProcess:
    def __init__(self, name: str, cmd: list[str], cwd: Path, health_url: str | None = None):
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.health_url = health_url
        self.process: subprocess.Popen | None = None
        self.started = False

    def start(self) -> None:
        print(f"[launch] starting {self.name} ...")
        try:
            self.process = subprocess.Popen(
                self.cmd,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
            threading.Thread(target=self._log_output, daemon=True).start()
        except FileNotFoundError as exc:
            print(f"[launch] skipped {self.name}: {exc}")
            return

        if self.health_url and self._wait_for_health(self.health_url, timeout=30):
            self.started = True
            print(f"[launch] {self.name} ready")
        elif self.health_url:
            print(f"[launch] {self.name} did not become healthy within timeout")
        else:
            self.started = True
            print(f"[launch] {self.name} started (no health check)")

    def _log_output(self) -> None:
        if not self.process:
            return
        for line in self.process.stdout:
            line = line.rstrip()
            if line:
                print(f"[{self.name}] {line}")

    def _wait_for_health(self, url: str, timeout: int = 30) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                with urllib.request.urlopen(url, timeout=1) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                time.sleep(0.3)
        return False

    def stop(self) -> None:
        if not self.process:
            return
        print(f"[launch] stopping {self.name} ...")
        try:
            self.process.send_signal(signal.CTRL_BREAK_EVENT if sys.platform == "win32" else signal.SIGTERM)
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
        except Exception as exc:
            print(f"[launch] error stopping {self.name}: {exc}")
        print(f"[launch] {self.name} stopped")


def _check_go_available() -> bool:
    try:
        subprocess.run(["go", "version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _check_npm_available() -> bool:
    try:
        subprocess.run(["npm", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def build_plan(args: argparse.Namespace) -> list[ComponentProcess]:
    plan: list[ComponentProcess] = []

    plan.append(ComponentProcess(
        name="backend",
        cmd=BACKEND_CMD,
        cwd=REPO_ROOT,
        health_url=BACKEND_URL,
    ))

    if args.distributed or args.all:
        if not _check_go_available():
            print("[launch] Go toolchain not found; skipping distributed components")
            return plan

        plan.append(ComponentProcess(
            name="control-plane",
            cmd=GO_CONTROLPLANE_CMD,
            cwd=REPO_ROOT / "go",
            health_url=GO_HEALTH_URL,
        ))

        plan.append(ComponentProcess(
            name="billing",
            cmd=GO_BILLING_CMD,
            cwd=REPO_ROOT / "go",
            health_url=GO_BILLING_HEALTH_URL,
        ))

        worker_count = args.workers if args.workers > 1 else 1
        for i in range(worker_count):
            plan.append(ComponentProcess(
                name=f"worker-{i + 1}",
                cmd=GO_WORKER_CMD,
                cwd=REPO_ROOT / "go",
                health_url=None,
            ))

    if args.cloud or args.all:
        if not _check_go_available():
            print("[launch] Go toolchain not found; skipping cloud components")
            return plan

        plan.append(ComponentProcess(
            name="cloud-gateway",
            cmd=CLOUD_GATEWAY_CMD,
            cwd=REPO_ROOT / "cloud",
            health_url=CLOUD_GATEWAY_HEALTH_URL,
        ))
        plan.append(ComponentProcess(
            name="cloud-auth",
            cmd=CLOUD_AUTH_CMD,
            cwd=REPO_ROOT / "cloud",
            health_url=CLOUD_AUTH_HEALTH_URL,
        ))
        plan.append(ComponentProcess(
            name="cloud-tunnel",
            cmd=CLOUD_TUNNEL_CMD,
            cwd=REPO_ROOT / "cloud",
            health_url=CLOUD_TUNNEL_HEALTH_URL,
        ))

    if args.frontend or args.all:
        if _check_npm_available():
            plan.append(ComponentProcess(
                name="frontend",
                cmd=FRONTEND_CMD,
                cwd=REPO_ROOT / "web",
                health_url=FRONTEND_URL,
            ))
        else:
            print("[launch] npm not found; skipping frontend dev server")

    return plan


def main(args: argparse.Namespace | None = None) -> int:
    if args is None:
        parser = argparse.ArgumentParser(
            prog="prometheus launch",
            description="Launch the full Prometheus platform with one command",
        )
        parser.add_argument(
            "--distributed", action="store_true",
            help="start Go distributed services",
        )
        parser.add_argument(
            "--cloud", action="store_true",
            help="start Go cloud services",
        )
        parser.add_argument(
            "--frontend", action="store_true",
            help="start Vite dev server",
        )
        parser.add_argument(
            "--all", action="store_true",
            help="start every subsystem",
        )
        parser.add_argument(
            "--workers", type=int, default=1,
            help="number of local Go workers (default: 1)",
        )
        args = parser.parse_args()

    if not (args.distributed or args.cloud or args.frontend or args.all):
        args.all = True

    plan = build_plan(args)
    if not plan:
        print("[launch] nothing to start")
        return 1

    print("=" * 60)
    print(" Prometheus Engineering Intelligence Platform — launcher")
    print("=" * 60)
    for comp in plan:
        print(f"  • {comp.name}")
    print("=" * 60)

    for comp in plan:
        comp.start()

    started = [c for c in plan if c.started]
    if not started:
        print("[launch] no components started successfully")
        return 1

    print()
    print("[launch] platform online")
    print(f"[launch] backend API:  {BACKEND_URL.replace('/health', '')}")
    if any(c.name == "frontend" for c in started):
        print(f"[launch] frontend:     {FRONTEND_URL}")
    if any(c.name == "control-plane" for c in started):
        print(f"[launch] control plane: http://127.0.0.1:8080 (gRPC :8082)")
    if any(c.name == "cloud-gateway" for c in started):
        print(f"[launch] cloud gateway: http://127.0.0.1:8080")
    print("[launch] press Ctrl+C to stop\n")

    stop_event = threading.Event()

    def _signal_handler(signum, frame):
        print("\n[launch] shutdown requested")
        stop_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        while not stop_event.is_set():
            for comp in started:
                if comp.process and comp.process.poll() is not None:
                    print(f"[launch] {comp.name} exited with code {comp.process.returncode}")
                    stop_event.set()
                    break
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for comp in started:
            comp.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
