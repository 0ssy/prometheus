"""Build the self-contained Prometheus backend executable (Tauri sidecar).

Freezes ``prometheus.py`` into a single Windows executable that runs the API
server. The output is copied into ``src-tauri/binaries/`` with the
target-triple suffix Tauri expects for an ``externalBin`` sidecar, so
``cargo tauri build`` bundles a fully self-contained installer.

Usage:
    python scripts/build_app_exe.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = ROOT / "src-tauri" / "binaries"
OUTPUT_NAME = "prometheus-x86_64-pc-windows-msvc.exe"

# First-party top-level packages. ``prometheus.py`` launches the server via
# ``uvicorn.run(app, ...)`` today, but it historically used a string import
# ("backend.main:app") that PyInstaller cannot trace, so we list every
# first-party package as a hidden import to be safe.
FIRST_PARTY = [
    "agents", "api", "contracts", "core", "delta", "devices", "digital_twin",
    "distributed", "engineering", "epsilon", "firmware", "hardware",
    "implementations", "kernel", "knowledge", "marketplace", "memory", "omega",
    "policy", "protocols", "reasoning", "runtime_management", "security",
    "services", "simulation", "workflow", "autonomous", "sdk", "dashboard",
    "experiments", "labs", "benchmarks", "verification", "backend",
]

HOOKS_DIR = ROOT / "pyinstaller_hooks"


def main() -> int:
    if shutil.which("pyinstaller") is None:
        print("ERROR: pyinstaller is not installed. Run: pip install pyinstaller", file=sys.stderr)
        return 1

    args = [
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--name", "prometheus",
        "--clean",
        f"--additional-hooks-dir={HOOKS_DIR}",
    ]
    for pkg in FIRST_PARTY:
        args += ["--hidden-import", pkg]
    # Bundle the built SPA so the frozen backend can serve it at /dashboard.
    args += ["--add-data", f"{ROOT / 'web' / 'dist'}{os.pathsep}web/dist"]
    args.append(str(ROOT / "prometheus.py"))

    print("Building Prometheus backend executable...")
    proc = subprocess.run([sys.executable, "-m", *args], cwd=ROOT)
    if proc.returncode != 0:
        return proc.returncode

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    src = ROOT / "dist" / "prometheus.exe"
    dst = BIN_DIR / OUTPUT_NAME
    shutil.copyfile(src, dst)
    print(f"Sidecar written to {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
