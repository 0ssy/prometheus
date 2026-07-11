# Plan: Fix Scaling, Crash, and Stability Issues

## Context
A performance/stability test pass surfaced four concrete defects in the running codebase. This plan fixes them. No source should be changed outside these steps.

## Goals
- `/knowledge/graph` must not OOM the process or browser at scale.
- A corrupted SQLite DB must not prevent Prometheus from booting.
- `ResourceManager.to_dict()` must never raise `AttributeError`.
- A misbehaving plugin must not hang a worker thread or crash the process.

## Out of Scope
- Full graph virtualization / canvas/WebGL rendering (user confirmed UI design is accepted).
- Swapping to PostgreSQL.
- Implementing the Project Aether Rust runtime (future milestone).

---

## Task 1 — Cap `/knowledge/graph` response size (backend)

**File:** `backend/main.py` (`/knowledge/graph` endpoint, lines 994-1024)

**Change:**
- Import `current_app` config or read env var `PROMETHEUS_GRAPH_NODE_LIMIT` (default 10000).
- After fetching `nodes` and `edges` from the DB, if `len(nodes) > limit`, truncate to `limit`.
- Return an extra field in the JSON response: `truncated: true` and `truncated_total: raw_count`.

**Rationale:** The endpoint currently does `db.query(...).all()` with no limit. At 500K target this is multi-second, multi-MB response. A hard cap plus a flag lets the frontend decide to tell the user "show me more" without changing the existing rendering pattern.

**Validation:**
- Seed 30K nodes/edges in a test, call `/knowledge/graph`, assert `len(response["nodes"]) <= 10000` and `truncated is True`.

---

## Task 2 — Cap graph data accepted by frontend renderer (frontend)

**File:** `web/src/apps/KnowledgeApp.ts`

**Change:**
- After `api.knowledgeGraph()` resolves, clamp `nodes` and `edges` to the same limit before passing to `computePositions()`/`renderGraph()`.
- If `nodes.length` or `edges.length` exceeds the limit, display "+X more facts" in the stats area instead of crashing the tab.

**Rationale:** Defensive in case an older backend or manual call exceeds the limit. Keeps the user's existing DOM-based renderer from tab-locking without changing the visual design.

**Validation:**
- Manual: open DevTools, inject an array of 50K nodes into the graph response, confirm the stats bar shows a cap message and the tab stays responsive.

---

## Task 3 — Recover from corrupted SQLite DB on boot

**Files:**
- `core/database.py` (`init_db`, lines 55-64)
- `backend/main.py` (`startup`, lines 81-86)

**Change:**
- Wrap `Base.metadata.create_all(bind=engine)` in `try/except sqlite3.DatabaseError`.
- If the DB file exists and `create_all` fails with `sqlite3.DatabaseError`, log the path, move it to `<path>.corrupted.<timestamp>`, then retry `create_all` on a fresh file.
- The retry will self-heal with an empty schema.
- Optionally surface the event via an `event_bus` publish so the UI can alert the user.

**Rationale:** A bad shutdown or disk fault can leave a valid-size file with an invalid header. Current behavior: unhandled exception, process exit code 3, app never starts. New behavior: quarantine corrupt file, recreate schema, boot continues.

**Validation:**
- Create a SQLite file at `config.db_path` with garbage bytes, start the app, assert `/health` returns `ok` and a new fresh DB exists alongside the quarantined corrupt file.

---

## Task 4 — Initialize `_throttled` and `_throttle_reason` in both ResourceManagers

**Files:**
- `omega/runtime_management/resource_manager.py` (`__init__`, line 29)
- `runtime_management/resource_manager.py` (`__init__`, line 29)

**Change:**
In both `ResourceManager.__init__`() methods, add:
```python
self._throttled = False
self._throttle_reason = None
```

**Rationale:** Both classes share identical code and both are missing these attributes. `to_dict()` references them at line 82-83, so any endpoint that calls it (e.g., `/system/resources`) will crash with `AttributeError` before first failure or explicit throttle call. The test run already hit this once; it is resolved only if the attrs are initialized at construction time.

**Validation:**
- Instantiate `ResourceManager()`, call `.to_dict()`, assert no exception and `"throttled": False`.

---

## Task 5 — Plugin error handling and timeout

**File:** `plugins/manager.py` (`run`, lines 41-47)

**Change:**
- Wrap `plugin.run(context)` in `try/except Exception as exc`, log the exception, publish a `PluginErrorEvent` (or reuse existing event bus with a structured payload), and return `{"error": str(exc)}` instead of raising.
- Add a configurable `timeout: float | None = None` kwarg to `run`. Use `signal.alarm` (Unix) or `threading.Timer` (fallback) to abort hung plugins after the timeout. Aborted plugins must return `{"error": "timeout"}` and log a warning.

**Rationale:** A plugin that hangs ties up a FastAPI worker thread forever. A plugin that raises crashes the request boundary but is otherwise harmless under FastAPI today. The manager should isolate both cases so future Prometheus features (e.g., plugin-to-plugin pipelines) are not fragile.

**Validation:**
- Register a crash plugin whose `run()` raises `Exception("boom")`, call `run`, assert result contains `error`.
- Register a sleep plugin with `time.sleep(10)`, call `run` with `timeout=0.5`, assert result contains `timeout` and the call returns within ~1s.

---

## Test Additions

**New test file:** `tests/test_knowledge_graph_scaling.py`
- Test `/knowledge/graph` truncates at the limit and returns `truncated: true` when over.
- Test with exactly at limit returns `truncated: false`.

**New test file:** `tests/test_database_corruption_recovery.py`
- Write garbage to `config.db_path`, call `init_db()`, assert no exception, assert fresh schema exists, assert corrupt file was moved to `*.corrupted.*`.

**Update:** `tests/test_runtime_management.py`
- Add assertions that `ResourceManager().to_dict()["throttled"] is False`.

**Update:** `tests/test_plugin_manager.py` (create if missing, else extend existing)
- Add crash-plugin and timeout-plugin tests described above.

---

## Rollout Order
1. Task 4 (ResourceManager init) — lowest risk, immediate crash fix.
2. Task 3 (DB corruption recovery) — prevents total boot failure.
3. Task 1 (graph cap) + Task 2 (frontend clamp) — shipped together to keep backend and frontend expectation aligned.
4. Task 5 (plugin safety) — after the stability fixes so regressions are easier to isolate.

---

## Risks
- Graph truncation hides data. Plan an upper-bound indicator (+X more) in the UI so users know they are not looking at everything.
- `.corrupted.*` file rollover could fill disk on repeated corruption. Add a TTL or max count if this becomes a user-reported issue (out of scope for the first pass; the path should be short-lived).
