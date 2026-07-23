"""
prome — Prometheus Platform bootstrap / installer launcher.

Usage:
    python prome.py install      # first-time setup: venv + deps + C++ HAL
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


def _cmake_path() -> str | None:
    return which("cmake")


def _ensure_cpp_toolchain() -> bool:
    cmake = _cmake_path()
    if not cmake:
        print("CMake not found in PATH. Install from https://cmake.org/")
        return False
    r = _run([cmake, "--version"], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"CMake: {r.stdout.strip().splitlines()[0]} OK")
        return True
    return False


def _build_hal_core() -> bool:
    cmake = _cmake_path()
    if not cmake:
        return False
    build_dir = REPO_ROOT / "build"
    print("Building C++ HAL core...")
    r1 = _run([cmake, "-B", str(build_dir), "-S", str(REPO_ROOT / "cpp")], cwd=REPO_ROOT)
    if r1.returncode != 0:
        print(f"CMake configure failed (rc={r1.returncode})")
        return False
    r2 = _run([cmake, "--build", str(build_dir), "--config", "Release"], cwd=REPO_ROOT)
    if r2.returncode == 0:
        print("C++ HAL built OK")
        return True
    print(f"C++ HAL build failed (rc={r2.returncode})")
    return False


def cmd_install() -> int:
    if not _check_python():
        return 1
    pip = _ensure_venv()
    py_ok = _install_python_deps(pip)
    cpp_ok = _ensure_cpp_toolchain()
    hal_ok = _build_hal_core() if cpp_ok else False
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
    hal_so = REPO_ROOT / "build" / "Release" / "hal_core.dll"
    print(f"cpp/hal    : {'built' if hal_so.exists() else 'missing'} ({hal_so})")
    cmake = _cmake_path()
    if cmake:
        r = _run([cmake, "--version"], capture_output=True, text=True)
        print(f"cmake     : {r.stdout.strip().splitlines()[0] if r.returncode == 0 else 'not found'}")
    else:
        print("cmake     : not found")
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
