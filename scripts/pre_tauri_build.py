"""Pre-Tauri build step with cross-platform Python lookup.

This is invoked by Tauri's ``beforeBuildCommand`` (run from the
``src-tauri/`` directory). It:

1. Builds the web SPA into ``web/dist`` (cross-platform ``npm`` call).
2. Locates the project's Python interpreter (preferring the ``venv``
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
    """Return the Python interpreter to drive the freeze step.

    Prefers the project ``venv`` (Windows ``Scripts`` / Unix ``bin``), then
    falls back to ``python3`` on ``PATH``, then to the current interpreter.
    """
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


def main() -> int:
    py = find_python()
    print(f"[pre_tauri_build] using python: {py}")

    npm = shutil.which("npm") or "npm"
    print("[pre_tauri_build] building web SPA...")
    subprocess.run([npm, "--prefix", "web", "run", "build"], cwd=str(ROOT), check=True)

    print("[pre_tauri_build] freezing backend sidecar...")
    subprocess.run([py, str(ROOT / "scripts" / "build_app_exe.py")], cwd=str(ROOT), check=True)

    print("[pre_tauri_build] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
