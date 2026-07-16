#!/usr/bin/env python3
"""
Prometheus — Unified Platform Entry Point (thin shim)

Delegates to the ``prometheus_cli`` package. Preserves the original CLI
interface so existing scripts and documentation remain valid.
"""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _prepend_runtime_paths() -> None:
    default_windows_paths = [
        r"C:\msys64\ucrt64\bin",
    ]
    configured = os.environ.get("PROMETHEUS_EXTRA_PATHS", "")
    configured_paths = [p.strip() for p in configured.split(os.pathsep) if p.strip()]
    candidates = configured_paths + default_windows_paths

    current_parts = os.environ.get("PATH", "").split(os.pathsep)
    normalized = {os.path.normcase(os.path.normpath(p)) for p in current_parts if p}

    to_prepend: list[str] = []
    for path in candidates:
        if not os.path.isdir(path):
            continue
        key = os.path.normcase(os.path.normpath(path))
        if key in normalized:
            continue
        to_prepend.append(path)
        normalized.add(key)

    if to_prepend:
        os.environ["PATH"] = os.pathsep.join(to_prepend + current_parts)


_prepend_runtime_paths()

from prometheus_cli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
