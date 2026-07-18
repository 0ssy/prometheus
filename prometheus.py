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

from core.bootstrap import boot
from core.config import config
from core.database import SessionLocal, create_engine, sessionmaker
from prometheus_cli import commands as _commands
from prometheus_cli.main import main


def _run_plugin(container, db) -> None:
    _commands._run_plugin(container, db)


def _run_agent(container, db) -> None:
    _commands._run_agent(container, db)


def _create_device(container, db) -> None:
    _commands._create_device(container, db)


def _store_memory(container, db) -> None:
    _commands._store_memory(container, db)


def _query_knowledge_graph(container, db) -> None:
    _commands._query_knowledge_graph(container, db)


def _build_twin(container, db) -> None:
    _commands._build_twin(container, db)


def _generate_report(container, db) -> dict:
    return _commands._generate_report(container, db)


def run_demo(db_path: str | None = None) -> dict:
    container = boot(_commands._heartbeat_job)

    if db_path:
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    else:
        engine = None
        SessionFactory = SessionLocal

    try:
        with SessionFactory() as db:
            _run_plugin(container, db)
            _run_agent(container, db)
            _create_device(container, db)
            _store_memory(container, db)
            _query_knowledge_graph(container, db)
            _build_twin(container, db)
            report = _generate_report(container, db)
            report["db_path"] = db_path or str(config.db_path)
    finally:
        container.get("scheduler").stop()
        if engine is not None:
            engine.dispose()

    return report


if __name__ == "__main__":
    raise SystemExit(main())
