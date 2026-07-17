"""Pre-Tauri build step with cross-platform Python lookup.

This is invoked by Tauri's ``beforeBuildCommand`` (run from the
``src-tauri/`` directory). It:

1. Builds the web SPA into ``web/dist`` (cross-platform ``npm`` call).
2. Builds the Zig hardware utilities (cross-platform ``zig build``).
3. Builds the C/C++ HAL static libraries (CMake).
4. Locates the project's Python interpreter (preferring the ``venv``
   created per ``src-tauri/README.md``) and uses it to freeze the
   backend sidecar via ``scripts/build_app_exe.py``.

Locating Python here (instead of hard-coding ``venv\\Scripts\\python.exe``)
keeps the same ``beforeBuildCommand`` usable from both Windows and
Unix CI hosts. Note that the actual installer target (``nsis``) is
Windows-only — see ``src-tauri/README.md``.

Usage (Tauri):

    python ../scripts/pre_tauri_build.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def find_python() -> str:
    venv = ROOT / "venv"
    if sys.platform.startswith("win"):
        candidate = venv / "Scripts" / "python.exe"
    else:
        candidate = venv / "bin" / "python"
    if candidate.exists():
        return str(candidate)
    if shutil.which("python3"):
        return "python3"
    return sys.executable


def build_zig() -> None:
    if not shutil.which("zig"):
        print("[pre_tauri_build] Zig not found; skipping Zig build")
        return
    print("[pre_tauri_build] building Zig hardware utilities...")
    subprocess.run(["zig", "build"], cwd=str(ROOT / "zig"), check=False)


def build_cpp_hal() -> None:
    cmake = shutil.which("cmake")
    if not cmake:
        print("[pre_tauri_build] CMake not found; skipping C/C++ HAL build")
        return
    build_dir = ROOT / "cpp" / "build"
    build_dir.mkdir(exist_ok=True)
    print("[pre_tauri_build] configuring C/C++ HAL...")
    subprocess.run(
        [cmake, "..", "-DBUILD_HAL_USB=ON", "-DBUILD_HAL_SERIAL=ON", "-DBUILD_HAL_GPIO=ON"],
        cwd=str(build_dir),
        check=False,
    )
    print("[pre_tauri_build] building C/C++ HAL...")
    subprocess.run([cmake, "--build", ".", "--config", "Release"], cwd=str(build_dir), check=False)


def main() -> int:
    py = find_python()
    print(f"[pre_tauri_build] using python: {py}")

    npm = shutil.which("npm") or "npm"
    print("[pre_tauri_build] building web SPA...")
    subprocess.run([npm, "--prefix", "web", "run", "build"], cwd=str(ROOT), check=True)

    build_zig()
    build_cpp_hal()

    print("[pre_tauri_build] freezing backend sidecar...")
    subprocess.run([py, str(ROOT / "scripts" / "build_app_exe.py")], cwd=str(ROOT), check=True)

    print("[pre_tauri_build] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
