"""
prome — Prometheus Platform bootstrap / installer launcher.

Usage:
    python prome.py install      # first-time setup: venv + deps + Rust crates
    python prome.py run          # start Prometheus
    python prome.py run --server # start server only
    python prome.py update       # pull + rebuild
    python prome.py status       # show versions / paths
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from shutil import which

REQUIRED_PYTHON = (3, 11)
REPO_ROOT = Path(__file__).resolve().parent


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, **kwargs)


def _check_python() -> bool:
    v = sys.version_info
    ok = v >= REQUIRED_PYTHON
    print(f"Python {v.major}.{v.minor}.{v.micro} {'OK' if ok else 'NEED 3.11+'}")
    return ok


def _ensure_venv() -> Path:
    venv = REPO_ROOT / "venv"
    pip = venv / "Scripts" / "pip.exe" if sys.platform == "win32" else venv / "bin" / "pip"
    if not venv.exists():
        print("Creating virtual environment...")
        _run([sys.executable, "-m", "venv", "venv"], cwd=REPO_ROOT)
    if not pip.exists():
        print("ERROR: pip not found in venv. Recreate the venv manually.")
        sys.exit(1)
    return pip


def _install_python_deps(pip: Path) -> bool:
    print("Installing Python dependencies...")
    result = _run([str(pip), "install", "-r", str(REPO_ROOT / "requirements.txt")], cwd=REPO_ROOT)
    return result.returncode == 0


def _cargo_path() -> str | None:
    return which("cargo")


def _ensure_rust() -> bool:
    cargo = _cargo_path()
    if not cargo:
        print("Rust/cargo not found in PATH. Install from https://rustup.rs/")
        return False
    r = _run([cargo, "--version"], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"Rust toolchain: {r.stdout.strip()} OK")
        return True
    return False


def _build_hal_core() -> bool:
    cargo = _cargo_path()
    if not cargo:
        return False
    print("Building Rust HAL core...")
    r = _run([cargo, "check", "-p", "hal-core", "--lib"], cwd=REPO_ROOT / "crates")
    if r.returncode == 0:
        print("hal-core built OK")
        return True
    print(f"hal-core build failed (rc={r.returncode})")
    return False


def cmd_install() -> int:
    if not _check_python():
        return 1
    pip = _ensure_venv()
    py_ok = _install_python_deps(pip)
    rs_ok = _ensure_rust()
    hal_ok = _build_hal_core() if rs_ok else False
    if py_ok and hal_ok:
        print("\nPrometheus is ready. Run: python prome.py run")
        return 0
    return 1


def cmd_run() -> int:
    if not (REPO_ROOT / "venv").exists():
        print("venv not found. Run: python prome.py install")
        return 1
    entry = REPO_ROOT / "prometheus.py"
    print(f"Starting Prometheus: python {entry}")
    return subprocess.run([sys.executable, str(entry)]).returncode


def cmd_status() -> int:
    print(f"Repo root : {REPO_ROOT}")
    print(f"Python    : {sys.version}")
    venv = REPO_ROOT / "venv"
    print(f"venv      : {'present' if venv.exists() else 'missing'}")
    hal_lib = REPO_ROOT / "target" / "debug" / "libhal_core.dll"
    print(f"hal-core   : {'built' if hal_lib.exists() else 'missing'}")
    cargo = _cargo_path()
    if cargo:
        r = _run([cargo, "--version"], capture_output=True, text=True)
        print(f"cargo     : {r.stdout.strip() if r.returncode == 0 else 'not found'}")
    else:
        print("cargo     : not found")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip())
        return 0
    cmd = sys.argv[1].lower().replace("-", "_")
    dispatch = {
        "install": cmd_install,
        "run": cmd_run,
        "update": cmd_install,
        "status": cmd_status,
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"Unknown command: {cmd}")
        print(__doc__.strip())
        return 1
    return fn()


if __name__ == "__main__":
    sys.exit(main())
