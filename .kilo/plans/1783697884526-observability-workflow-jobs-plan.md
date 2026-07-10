# Prometheus Operational Tooling Plan — System Monitor, Resource Manager, Job Scheduler, Workflow Engine + Baseline

## Context (what already exists)

The building blocks for all four items are already in the codebase; they are simply not
exposed to the UI or tracked with runtime state:

- `core/observability.py` — `ObservabilityStore` (metrics, traces, event history) → `GET /observability`.
- `omega.runtime_management.resource_manager.ResourceManager` (psutil CPU/mem/disk/net) — **registered as `omega_resource_manager` in the container** (`core/bootstrap.py:145`) but **no endpoint exposes it**.
- `core/scheduler.py` — `TaskScheduler` with `list_jobs()` (names only). No per-job state, retries, pause/resume, or detail endpoint.
- `agents/planner.py` — `TaskGraph` / `TaskNode` DAG with topological sort (planner exists; **no runtime that executes a graph**).
- `services/platform_service.py:run_beta_workflow` — a hardcoded device workflow (Connect→Simulate→Reason→Record). Proves the shape; not generalized.
- Frontend `Desktop.ts` — apps are registered in three places: `APPS`, `DOCK_KEYS`, `DOCK_ICONS`. `Store.ts` polls `/status` every 5s and consumes `/events` SSE. `KernelApp`, `ActivityApp`, and the desktop `#stat-grid` all render overlapping subsystem status → **duplication to consolidate**.

This plan exposes the existing data, adds runtime state where missing, and unifies the
fragmented status views into one OS-style monitor — satisfying the "every new subsystem
must remove complexity elsewhere" rule.

---

## Guiding rule applied throughout

> Each new subsystem MUST retire an equivalent amount of existing complexity.

Concretely: the new **Monitor app folds in `KernelApp` + `ActivityApp` + the
`#stat-grid` block** in `Desktop.ts`. Workflow Engine **reuses `TaskGraph`/`TaskPlanner`**
(no new planner). Job Scheduler **extends `TaskScheduler`** (no second scheduler).
Resource panel **wraps the existing `omega_resource_manager`** (no new resource module).

---

## Backend tasks

### B1. Resource usage endpoint (Resource Manager)
- Add `GET /system/resources` in `backend/main.py` returning
  `container.get("omega_resource_manager").get_usage()` as a dict
  (`cpu_percent`, `memory_mb`, `disk_mb`, `network_mbps`, `active_connections`),
  plus `limits` and `throttled`/`throttle_reason` if exposed by the manager.
- Convert `ResourceUsage` dataclass → dict at the boundary (add a `to_dict()` or do it inline).

### B2. Observability rates + subsystem status
- Extend `ObservabilityStore` (`core/observability.py`):
  - Track a sliding-window timestamp list so `snapshot()` can compute
    `events_per_sec` and `commands_per_sec` over the last 60s.
  - Add counters for `commands` (record on capability execute) — hook via the
    existing `record_event`/`increment` paths used by `event_handlers.py` and
    `platform_service._trace`.
  - Add a `subsystems` section to `snapshot()` summarizing live subsystem
    status from the container (kernel, knowledge, simulation, reasoning, hardware,
    agents, plugins, devices, workflows, background tasks, storage) — read from
    existing `/status`/`/stats` data rather than new state.
- `GET /observability` already returns `snapshot()`; no new endpoint needed.

### B3. Job Scheduler runtime state (Job Scheduler UI)
- Extend `core/scheduler.py` `TaskScheduler` to track per-job records:
  `name`, `interval_seconds`, `status` (`scheduled`|`running`|`paused`|`completed`|`failed`),
  `last_run`, `next_run`, `failures`, `retries`, `last_error`.
  - Wrap the call in `_run_loop` to set `running`→`completed`/`failed`, increment `failures`, honor a `max_retries` and exponential backoff, and set `paused` jobs to skip.
  - Add `pause(name)` / `resume(name)` / `trigger(name)` and `jobs_detail() -> list[dict]`.
- Update `contracts/scheduler.py` `SchedulerApi` with the new abstract methods.
- Add `GET /system/jobs` (detail list) and `POST /system/jobs/{name}/{action}`
  where `action ∈ {pause,resume,trigger}`.

### B4. Workflow Engine runtime + API
- New module `workflow/runtime.py` — `WorkflowRuntime`:
  - A workflow = ordered `TaskGraph` of steps; each step maps to an
    **action** (`capability:<name>` | `agent:<name>` | `memory:remember` | `notify`).
  - Execute steps in topological order; each step has state
    (`pending`|`running`|`done`|`failed`|`skipped`). On failure, halt the chain
    (record `failed_at`). Reuse `TaskGraph.topological_sort()`.
  - Persist workflows to `config/workflows.json` (list of `{id, name, steps, status, last_run, results}`).
  - Seed one default workflow from your example:
    `Connect Device → Identify → Create Digital Twin → Run Diagnostics → Store Knowledge → Generate Report → Notify User`.
- Register `workflow_runtime` in `core/bootstrap.py` container.
- Endpoints in `backend/main.py`:
  - `GET /workflows` (list + statuses)
  - `POST /workflows` (create `{name, steps[]}`)
  - `POST /workflows/{id}/run`
  - `GET /workflows/{id}` (live step states + results)

### B5. Performance & quality baseline
- Capture a baseline on first boot into `config/baseline.json`:
  - backend startup time (instrument `boot()` in `core/bootstrap.py` with stage timings:
    DB load, service registration, plugins, agents, scheduler start),
  - initial memory (from `omega_resource_manager`), idle CPU sample, plugin count, agent count.
- Add `GET /system/baseline` to read it; `POST /system/baseline/refresh` to re-capture.
- Add per-stage boot timings to the **frontend** `BootSequence.ts` (already has a
  single timer — record `performance.now()` deltas per `BOOT_LINES` stage and show
  them in the `SYSTEM SUMMARY` block, matching your requested format:
  `Kernel Initialization 317 ms` / `Plugin Loading 118 ms` / `Total 739 ms`).

---

## Frontend tasks

### F1. New `MonitorApp` (System Monitor — consolidates Kernel + Activity + stat-grid)
- `web/src/apps/MonitorApp.ts`: polls `/system/resources` (~2s), `/observability`
  (~2s), `/system/jobs` (~2s), `/workflows` (~3s). Renders OS-monitor panels:
  - CPU / Memory / Disk / Network gauges (usage vs limit bars).
  - Subsystem status grid (kernel, knowledge, simulation, reasoning, hardware,
    agents, plugins, devices, workflows, background tasks, storage).
  - Live counters: Events/sec, Commands/sec.
  - Connected devices, active workflows, running jobs.
- After `MonitorApp` lands, **deprecate `KernelApp` and `ActivityApp`** and
  **remove the duplicated `#stat-grid` rendering block** in `Desktop.ts`
  (`renderStatGrid`) — this is the explicit complexity-removal payoff.

### F2. `JobsApp` (Job Scheduler UI)
- `web/src/apps/JobsApp.ts`: lists jobs from `/system/jobs` with state badges
  (scheduled/running/paused/completed/failed), failure count, next-run ETA, and
  pause/resume/trigger buttons → `POST /system/jobs/{name}/{action}`.
- Filter chips by state; show queue (paused vs running).

### F3. `WorkflowApp` (Workflow Engine UI)
- `web/src/apps/WorkflowApp.ts`: lists workflows as **visual step chains**
  (box-per-step + connector arrows) with live step-state colors. "Run" button →
  `POST /workflows/{id}/run`; poll `GET /workflows/{id}` for progress.
  "New Workflow" form (name + ordered step list) → `POST /workflows`.
- **Out of scope (note, do not build now):** drag-and-drop editor. The data model
  (ordered steps) is chosen so a future editor drops in without a migration.

### F4. App registration + boot timing + API client
- `web/src/api/client.ts`: add `systemResources()`, `systemJobs()`, `workflows()`,
  `baseline()`, and reuse `observability()`/`status()`.
- `web/src/apps/index.ts`: export `mountMonitor`, `mountJobs`, `mountWorkflow`.
- `web/src/os/Desktop.ts`: add `monitor`, `jobs`, `workflow` to `APPS`,
  `DOCK_KEYS`, and `DOCK_ICONS` (new simple SVG icons). Wire keyboard slots if
  dock order changes.
- `BootSequence.ts`: per-stage timing as in B5.

---

## Validation

- `python -m pytest` green; **add/extend tests**:
  - `tests/test_scheduler.py`: pause/resume/trigger, failure→retry→failed, `jobs_detail()` shape.
  - `tests/test_workflow_runtime.py`: DAG executes in order; failure halts chain;
    persistence to `config/workflows.json`; seeded default workflow present.
  - `tests/test_observability.py`: `events_per_sec`/`commands_per_sec` computed.
  - `tests/test_resources_endpoint.py`: `/system/resources` returns dict via `omega_resource_manager`.
- Frontend: `npm run build` succeeds (no TS errors).
- Manual smoke (dev server): open Monitor → gauges populate; trigger a job pause/resume;
  run the seeded workflow → steps turn green in order; confirm no new `500`s in backend log
  (the prior `esp32_01` ownership 500 is already fixed).
- Baseline: `GET /system/baseline` returns captured metrics; re-capture works.

## Risks / notes
- `ResourceManager.get_usage()` swallows `ImportError` (psutil) with zeros — acceptable,
  but note in UI when psutil is absent.
- `omega_resource_manager` vs the standalone `runtime_management/resource_manager.py`
  are near-duplicates; this plan intentionally uses only the registered one. Flag the
  standalone as dead code to remove in a follow-up (further complexity reduction).
- No DB migrations needed; workflow state is JSON-file backed.

## Open questions (non-blocking)
- Should workflows be user-creatable in v1, or seeded-only (UI lists + runs, no create form)?
  Plan assumes creatable; easy to cut to seeded-only if preferred.
- Retry policy default: plan assumes `max_retries=3` with backoff for scheduler jobs.
