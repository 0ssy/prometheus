# Prometheus Experience Layer — Phase 1: The CLI "Face"

## Context

The manifesto argues Prometheus has an **identity / product problem**: you launch it with
`python prometheus.py` or `uvicorn backend.main:app`, which "screams backend," not
"Engineering OS." Grounding that claim against the actual repo:

- A unified entry point **already exists**: `prometheus.py` (`runtime` / `api` / `demo` /
  `test` subcommands) and `main.py`.
- A status report **already exists** inside `run_demo()` (`prometheus.py:137-156`): it counts
  kernel, plugins, agents, devices, services, memory entries, knowledge facts.
- A dashboard **already exists**: mounted at `/dashboard` (`backend/dashboard.py`) plus
  `omega/dashboard/{section}` JSON APIs and the `dashboard/` module.

So the real gaps are narrow and outward-facing, not architectural:

1. **No installable `prometheus` command** — there is no `pyproject.toml`/`setup.py`, so you
   must type `python prometheus.py`. This is the dominant "it screams backend" symptom.
2. **No OS-style banner on launch** — the status report only appears as a side-effect of
   `demo`, and it is plain JSON-as-log, not a branded face.
3. **No one-command way to open the dashboard.**

### Deliberately OUT OF SCOPE (per the manifesto's own advice)
> "Identity problems are solved with design, workflows, UX — not by rewriting the architecture."

- **Do NOT** physically restructure the engine code into `kernel/ runtime/ workspace/
  studio/ dashboard/ explorer/ shell/` folders. The internal layout is fine; this plan only
  adds an outward face.
- The "alive, connected, clickable knowledge graph" dashboard rebuild is **Phase 2**, a
  separate plan, built on top of the existing `dashboard/` module — not this plan.

## Design Spec — Phase 2 dashboard visual target

Reference aesthetic (inferred from the user's "hermes agent" link — Hermes Agent web dashboard
docs/PRs; I could not view the actual screenshot): a clean **admin/ops console** — sidebar nav +
KPI/status cards + live activity feed + health badges, responsive, real-time.

- **Color tokens (user-provided direction — exact hex TBD, propose starting values):**
  - Background: *dull / dark cream* → start `#211F1A` (dark warm beige) for the app shell, with
    raised surfaces at `#2A2823`. (Confirm: "darky cream" is ambiguous — could also be a light
    muted beige `#EDE7D9`. Pick one and lock it.)
  - Wordmark / primary accent: *sky blue* → start `#5AB9EA` for the "Prometheus" logo + primary
    actions/links.
  - Text: warm off-white `#EDE7D9` on the dark cream; muted `#9A9384` for secondary.
  - Status semantics: `Running`/`Healthy`/`Active` = sky blue or soft green; `Idle` = muted
    amber; `Stopped`/`Error` = muted red.
- **Layout (Hermes-style):**
  - Left **sidebar**: Prometheus sky-blue wordmark at top; nav items mapping to the engines
    (Kernel, Knowledge, Simulation, Reasoning, Hardware, Agents, Capabilities, Learning) + a
    footer with version + org.
  - **Home = KPI/status cards**: one card per engine (Kernel/Knowledge/Simulation/Reasoning/
    Hardware) showing its live state, plus count cards (Connected Devices, Agents, Plugins,
    Capabilities, Knowledge Facts) — the same data the CLI banner shows.
  - **Activity feed**: live event stream from the existing `core/event_bus.py` (wire an SSE or
    WebSocket endpoint; do not invent a new event source).
  - **Health badges** per platform/service.
- **Behavior:** real-time updates (SSE/WebSocket over the existing event bus), responsive
  (hamburger on narrow viewports), dark theme by default (the cream shell).
- **Implementation note:** the current dashboard is **server-rendered** (`backend/dashboard.py`
  + `dashboard/` module + `omega/dashboard/{section}` JSON APIs). Phase 2 must decide: (a)
  restyle the existing server-rendered dashboard with the tokens above, or (b) add a small SPA
  (Vite + Tailwind) consuming the existing JSON APIs + a new SSE endpoint. Decision deferred to
  Phase 2; do **not** block Phase 1 on it.

## Goal
Make `prometheus` a real command that, on launch, shows a branded Engineering-OS status
banner and can open the dashboard — without touching internal engines. (The dashboard's
*visual* refresh is Phase 2, specified above.)

---

## Tasks

### 1. Add packaging so `prometheus` becomes an installable command
Create `pyproject.toml` at repo root. **Do not delete `requirements.txt`** — keep it as the
source of truth for runtime deps; `pyproject.toml` mirrors it (duplication noted as a known
cost; consolidate later if desired). Verified safe: no test imports the root `prometheus`
module, and no `[tool.pytest]` config exists, so adding this file does not change pytest
discovery.

```toml
# Packaging for the `prometheus` CLI face.
# Runtime deps are mirrored from requirements.txt (keep in sync by hand).
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "prometheus-engineering-os"
version = "0.6.0"   # matches core/config.py (0.6.0-omega); sync manually
description = "Prometheus Engineering OS — unified CLI face"
requires-python = ">=3.11"
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "sqlalchemy",
    "pydantic",
    "pyserial",
    "cryptography",
    "pytest",
]

[project.scripts]
prometheus = "prometheus:main"

[tool.setuptools]
py-modules = ["prometheus"]
```

Why this works:
- `main()` (`prometheus.py:176-208`) returns an `int`; setuptools console_scripts uses a
  non-None return value as the process exit code. Compatible as-is. And the console script
  calls `main()` directly, so the `if __name__ == "__main__"` guard in `prometheus.py:211`
  does **not** double-run it.
- `pip install -e .` puts the repo root on `sys.path`, so `import core`, `import backend`,
  `import kernel` resolve at runtime when the `prometheus` command is invoked.

Verify: `pip install -e .` then `prometheus --help` invokes `prometheus.py:main()`.

### 2. Refactor the status snapshot in `prometheus.py` (centerpiece: live internal-engine status)
Per the agreed scope, the face must surface the **live status of each internal engine**, not
just counts. Extract the report logic from `run_demo()` (`prometheus.py:137-156`) into a
reusable helper:

```python
def _status_snapshot(container: ServiceContainer, db) -> dict: ...
```

Map each banner line to a real, probed engine state from the booted container
(`core/bootstrap.py:95-144`):

| Banner line      | Source                                                    | Probe → label                     |
|------------------|-----------------------------------------------------------|-----------------------------------|
| Kernel           | `container.get("kernel")` (`PrometheusCoreKernel`)        | `.health()["status"] == "ok"` → `Running`, else `Stopped` |
| Knowledge        | `container.get("knowledge_engine")`                      | boot-success + non-empty graph → `Healthy`, else `Idle` |
| Simulation       | `simulation.engine.SimulationEngine`                     | **not registered in bootstrap** → `Idle` (honest; see Risks) |
| Reasoning        | `container.get("reasoning_api")`                         | boot-success → `Healthy`, else `Idle` |
| Hardware         | `device_api` + `hardware_hal`/`hardware_session_manager` | boot-success → `Idle` if no devices, else `Active` |
| Connected Devices| `device_api.list()` length                               | count                             |
| Agents           | `agent_api.list_agents()` length                         | count                             |
| Plugins          | `plugin_api.list_plugins()` length                       | count                             |
| Capabilities     | `capability_api.discover()` length                       | count                             |
| Knowledge Facts  | `SELECT count(*) FROM reasoning.KnowledgeFact`           | count                             |

State labels are `Running` / `Healthy` / `Active` / `Idle` / `Stopped`. **Be honest**: a
subsystem that is not wired/online prints `Idle` or `Stopped`, never a faked `Healthy`. This is
what makes it read as a real OS rather than a marketing screen.

### 3. Add a branded banner + `status` command to `prometheus.py`
- Add `status` subparser → boots, builds `_status_snapshot`, prints the banner, exits.
- Make a bare `prometheus` (no subcommand) print the banner + status by default
  (keep `--help` via `-h`).
- Banner format (matches the manifesto's example, driven by real data):

  ```
  Prometheus Engineering OS
  Version <config.version>

  Kernel...............Running
  Knowledge............Healthy
  Simulation...........Idle
  Reasoning............Healthy
  Hardware.............Idle

  Connected Devices....N
  Agents...............N
  Plugins..............N
  Capabilities.........N
  Knowledge Facts......N

  Ready.
  ```

### 4. Add a `dashboard` launch command to `prometheus.py`
Add a `dashboard` subparser that opens the existing dashboard in one step:
- Open the browser **after** the server is up: use `threading.Timer(1.5, webbrowser.open,
  args=[f"http://{config.api_host}:{config.api_port}/dashboard"]).start()`, then call
  `uvicorn.run("backend.main:app", host=..., port=..., reload=False)`.
- Print the URL and a hint before blocking. Keep `api` for "server only, no browser."
- `reload=False` (not `reload=True` like `run_api`) so the `webbrowser` import and timer live
  in the same process predictably.

### 5. Keep all existing entry points working
`runtime`, `api`, `demo`, `test` and the legacy `python main.py` / `uvicorn backend.main:app`
must remain unchanged in behavior. The new `prometheus` command wraps the same `boot()` path.

---

## Risks / failure modes

- **`Simulation` always shows `Idle`.** `SimulationEngine` (`simulation/engine.py`) exists but
  is **not registered in `core/bootstrap.py`** (no `container.register("simulation_engine", …)`),
  so the banner cannot probe it without either (a) lazily importing + constructing it, or
  (b) wiring it into bootstrap. Both are larger than this plan. Decision: print `Idle`
  honestly and file a follow-up to register the simulation engine in bootstrap so Phase 2 can
  show `Healthy`. Do **not** fake the state.
- **Editable install importability.** `pip install -e .` puts the repo root on `sys.path`, so
  `import core` / `import backend` resolve. If a consumer installs non-editably (`pip install .`)
  into a different cwd, the same still holds because the package root is on `sys.path`. Risk
  only if someone runs the console script from a dir that shadows `core`/`backend` — out of
  scope.
- **`status` is heavyweight.** Like `demo`, it boots the full platform (DB + scheduler +
  heartbeat). That is intentional (we want real engine state) but means `status` is not
  instant. Acceptable; do not weaken it to fake data.
- **Browser auto-open in headless/CI.** `webbrowser.open` is a no-op without a display; the
  server still starts and the URL is printed, so `dashboard` remains usable. Tests must not
  depend on a browser.
- **`pyproject.toml` vs `requirements.txt` drift.** Versions are duplicated by hand. Keep
  `requirements.txt` authoritative; note the duplication in a comment in `pyproject.toml`.

## Affected files
- `pyproject.toml` — **new** (packaging + console_scripts)
- `prometheus.py` — refactor report → `_status_snapshot`; add `status`, default banner,
  `dashboard` subcommands

## Validation
1. `pip install -e .` (in venv) succeeds; `prometheus --help` lists `runtime/api/demo/test/
   status/dashboard`.
2. `prometheus` (no args) and `prometheus status` print the branded banner with real counts.
3. `prometheus dashboard` opens `http://127.0.0.1:8000/dashboard` in a browser.
4. `prometheus demo` and `prometheus test` still pass (regression check incl.
   `tests/test_main_entrypoint.py`).
5. `python prometheus.py api` and `uvicorn backend.main:app` still work (legacy paths intact).
6. `pytest -q` green.

## Open questions (not blocking)
- **Exact color hex** for "dull/dark cream" background and "sky blue" wordmark — user to confirm
  the two starting values proposed in the Design Spec (and whether the cream shell is dark or
  light). Phase 1 banner is plain-text, so this only affects Phase 2.
- Register `SimulationEngine` in `core/bootstrap.py` so the banner can show `Healthy` instead
  of `Idle` — file as a follow-up; out of scope for this plan.
- Phase 2 dashboard: restyle the existing server-rendered `dashboard/` vs. add a small SPA over
  the existing JSON APIs + new SSE endpoint. Decision deferred to Phase 2.
