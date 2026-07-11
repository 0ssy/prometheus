# Tests

This folder holds the pytest suite for Prometheus. Tests are flat
(one file per subsystem) rather than nested by directory — the old
`core/`, `plugins/`, `memory/` ... layout described here previously no
longer matches the tree.

## Run everything

```bash
pytest
```

## Run a focused area

```bash
pytest tests/test_plugin_manager.py          # plugins
pytest tests/test_knowledge_graph_scaling.py # graph API + limits
pytest tests/test_database_corruption_recovery.py
pytest tests/test_installer_smoke.py         # clean-install boot check
```

## What's covered (high-risk areas first)

- `test_installer_smoke.py` — a clean install boots and `/health`,
  `/status`, `/docs` respond; a corrupted DB still boots (quarantine +
  recreate).
- `test_database_corruption_recovery.py` — SQLite corruption recovery.
- `test_knowledge_graph_scaling.py` — `/knowledge/graph` truncation.
- `test_plugin_manager.py` — error isolation + timeout for plugins.
- `test_runtime_management.py` — resource/lifecycle/memory managers.
- `test_bootstrap.py`, `test_container.py` — wiring and startup.
- `test_*_service.py` / `test_*_engine.py` — subsystem behavior.
- `test_event_bus_stress.py` — event-bus throughput under load.

## Conventions

- `tests/conftest.py` puts the repo root on `sys.path` and provides a
  `db_session` fixture backed by an in-memory SQLite engine.
- Boot-dependent tests use `fastapi.testclient.TestClient(app)` as a
  context manager so the startup event (and `boot()`) actually runs.
- Prefer small, behavior-focused tests; add a regression test for any
  defect you fix.
