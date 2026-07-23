# Known Limitations (v1.0.0-rc1)

This document tracks behaviors that are intentionally out of scope for the
`v1.0.0-rc1` tag. They are not release blockers but should be understood
by testers and operators.

## Packaging

- **Desktop installer is Windows-only (NSIS).** The Tauri build produces a
  Windows `.exe` installer (`src-tauri/target/release/bundle/nsis/
  Prometheus_0.6.0_x64-setup.exe`) that bundles a frozen Python backend.
  Linux (AppImage) and macOS (dmg) desktop packaging are **deferred to
  post-RC1**. The Python path
  (`pip install -r requirements.txt && python prometheus.py`) is the
  supported cross-platform install on non-Windows hosts.

## Framework / runtime

- **FastAPI `on_event` → `lifespan` migration — COMPLETE in RC1.**
  `backend/main.py` now uses a `lifespan` handler instead of the deprecated
  `@app.on_event("startup")`. No deprecation warning is emitted on boot.

## Data / persistence

- **Ontology is in-memory only.** The knowledge ontology is seeded with a
  starter taxonomy and held in memory; it is not persisted or loaded from
  the database.
- **No database migration system.** SQLite schemas are created fresh on
  boot via `init_db()`. A corrupted database is quarantined
  (`<path>.corrupted.<timestamp>`) and recreated, but there is no
  forward/backward schema migration tool yet.

## Plugins

- **Dynamic plugin discovery is not implemented.** Plugins are registered
  at bootstrap (see `core/bootstrap.py`) rather than discovered from the
  filesystem at runtime. A security model for arbitrary on-disk plugin
  loading is a prerequisite (tracked in `README.md` "What's deliberately
  NOT here yet").

## Tauri build prerequisites

- Building the desktop installer requires a Windows host with CMake + C++ compiler,
  Node 18+, Python 3.11+ on `PATH`, Microsoft WebView2 (preinstalled on
  Windows 10/11), NSIS (`makensis` on `PATH`), and a `venv` with
  `pyinstaller` installed. `python ../scripts/pre_tauri_build.py` locates the
  interpreter cross-platform, but the `nsis` bundle target itself is
  Windows-only.
