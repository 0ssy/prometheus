# Prometheus Core — Olympus (in progress)

## What this is

Prometheus Core includes Alpha foundation, Beta intelligence, Gamma knowledge, Delta simulation, Epsilon hardware abstraction, and Omega ecosystem:
knowledge graph, ontology, provenance, confidence-based facts, query engine, learning, digital twin, HAL, drivers, firmware intelligence, security, plugin SDK, multi-agent coordination, distributed runtime, policy engine, marketplace, enterprise configuration, runtime management, and unified dashboard.

| Deliverable            | File                                |
|-------------------------|--------------------------------------|
| Plugin architecture     | `plugins/base.py`, `plugins/manager.py` |
| Agent manager           | `agents/base.py`, `agents/manager.py`   |
| Platform contracts      | `contracts/`                            |
| Internal services       | `services/platform_service.py`, `services/event_handlers.py` |
| Implementations layer   | `implementations/platform_components.py` |
| Capability framework    | `core/capabilities.py`, `contracts/capability.py` |
| Reasoning pipeline      | `reasoning/pipeline.py` |
| Simulation engine       | `simulation/engine.py` |
| Core kernel             | `kernel/runtime.py` |
| Observability           | `core/observability.py` |
| Knowledge engine        | `knowledge/engine.py`, `knowledge/graph.py`, `knowledge/query.py` |
| Ontology + provenance   | `knowledge/ontology.py`, `knowledge/provenance.py` |
| Learning layer          | `knowledge/learning.py` |
| Event bus               | `core/event_bus.py`, `api/events.py`    |
| Long-term memory        | `memory/models.py`, `memory/store.py`   |
| Knowledge graph         | `reasoning/models.py`, `reasoning/graph.py` |
| Task scheduler          | `core/scheduler.py`                 |
| Local API               | `backend/main.py`                   |
| Local database          | `core/database.py`                  |
| Logging system          | `core/logger.py`                    |
| Configuration manager   | `core/config.py`                    |
| Unified entry point     | `prometheus.py`                      |

Everything runs locally on SQLite — no cloud dependency.

## Setup

```bash
cd prometheus
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Frontend (Engineering Dashboard)

The dashboard is a Vite + TypeScript SPA located in `web/`.

```bash
cd web
npm install
npm run typecheck
npm run lint
npm run build
```

Serve the built `web/dist/` alongside the FastAPI backend. The backend serves
the SPA at `/dashboard` and keeps `/docs` and `/omega/dashboard/{section}`
intact.

## Run it

```bash
# Unified entry point (runtime / api / demo / test):
python prometheus.py runtime
python prometheus.py api
python prometheus.py demo
python prometheus.py test

# Legacy entry points (still supported):
python main.py
uvicorn backend.main:app --reload
python happy_path.py
```

Server comes up on `http://127.0.0.1:8000`. Interactive API docs (auto-generated
by FastAPI) are at `http://127.0.0.1:8000/docs` — use this to click through
every endpoint without writing curl commands.

Engineering dashboard is at `http://127.0.0.1:8000/dashboard` — a pixel/CRT engineering workstation with an ASCII boot sequence, a windowed desktop (13 running applications), a persistent bottom terminal, and live activity feed.

## Verify the architecture vertical slice

```bash
# 1. Prometheus starts, loads plugins/agents
curl http://127.0.0.1:8000/health

# 2. Runs a plugin
curl -X POST http://127.0.0.1:8000/plugins/echo/run \
  -H "Content-Type: application/json" -d '{"message": "hello"}'

# 3. Dispatches an agent, which tracks a "device" in the knowledge graph
curl -X POST http://127.0.0.1:8000/agents/echo_agent/dispatch \
  -H "Content-Type: application/json" -d '{"device_id": "esp32_01", "status": "online"}'

# 4. Stores and recalls memory
curl -X POST "http://127.0.0.1:8000/memory?content=test&tag=milestone"
curl http://127.0.0.1:8000/memory

# 5. Queries the knowledge graph
curl "http://127.0.0.1:8000/knowledge?subject=esp32_01"

# 6. Lists capabilities (after registering devices)
curl "http://127.0.0.1:8000/capabilities"

# 7. Run Beta workflow (digital-device -> simulation -> reasoning)
curl -X POST "http://127.0.0.1:8000/beta/workflow/esp32_01?failure_mode=disconnect"

# 8. Query Gamma knowledge graph views
curl "http://127.0.0.1:8000/gamma/knowledge/devices-supporting-recovery"
curl "http://127.0.0.1:8000/gamma/knowledge/simulations-failed"
curl "http://127.0.0.1:8000/gamma/learning"
```

If all five return sensible JSON, the core platform orchestration is working end-to-end.

You can also run the full in-process demo:

```bash
python happy_path.py
```

This executes a complete slice:

`Platform Starts -> Plugin Loads -> Agent Registers -> Simulated Device Appears -> Knowledge Stored -> Task Scheduled -> Report Generated`

## Writing your first real plugin

Copy `plugins/installed/echo_plugin.py`. Your plugin must:
1. Subclass `PrometheusPlugin` (from `plugins/base.py`)
2. Implement `on_load()` and `run(context)`
3. Get registered by `core/bootstrap.py` during startup

Same pattern for agents — copy `agents/echo_agent.py`, subclass `PrometheusAgent`.

### Contract versioning rules (plugin compatibility)

Prometheus plugin contracts follow semantic versioning:

- `MAJOR`: breaking contract changes
- `MINOR`: backward-compatible contract additions
- `PATCH`: backward-compatible fixes/clarifications

Runtime contract version is defined in `contracts/versioning.py` as `CONTRACT_VERSION`.
Each plugin declares `required_contract_version` in `PrometheusPlugin`.

A plugin is load-compatible when:

- `required_contract_version.major == CONTRACT_VERSION.major`
- `required_contract_version <= CONTRACT_VERSION` (minor/patch)

If incompatible, plugin registration fails fast with a clear error.

## What's deliberately NOT here yet

- Dynamic plugin discovery from the filesystem (Phase Beta+, needs a security model first)
- Real device I/O — cameras, GPIO, ESP32/UART (Phase Beta)
- Firmware inspection, boot chain analysis (Phase Gamma)
- Digital twin modeling beyond flat knowledge-graph facts (Phase Delta)
- Postgres (swap is one line in `core/database.py` when you need it — change
  the SQLite URL to a Postgres URL, same `engine`/`Session` pattern holds)

Don't build these now. Get comfortable extending plugins/agents on top of
this skeleton first — that's the actual Phase Alpha goal.

## Roadmap (RFC-governed phases)

| Version | Codename | Phase |
|---------|----------|-------|
| v0.1.0-alpha | Genesis | Foundation |
| v0.2.0-beta | Atlas | Reasoning + capabilities |
| v0.3.0-gamma | Helios | Knowledge + learning |
| v0.4.0-delta | Daedalus | Simulation + digital engineering lab |
| v0.5.0-epsilon | Hephaestus | Hardware abstractions + recovery planning |
| v1.0.0-omega | Olympus | Stable ecosystem + public APIs |

Roadmap changes are made deliberately through RFC updates.

## Gamma Helios knowledge workflow

```
User Request
      ↓
Capability Lookup
      ↓
Digital Device View
      ↓
Simulation Engine
      ↓
Reasoning Pipeline
      ↓
Recommendation
      ↓
Optional Capability Execution
      ↓
Knowledge Graph Search
      ↓
Related Devices + Capabilities + Past Simulations
      ↓
Recommendation + Learning record
```

## Delta/Epsilon/Omega upgrade endpoints

- Delta (Daedalus):
  - `POST /delta/lab/workspaces/{workspace_id}`
  - `POST /delta/lab/workspaces/{workspace_id}/failures`
  - `POST /delta/scenarios/{workspace_id}`
  - `GET /delta/time/battery-forecast`
- Epsilon (Hephaestus):
  - `POST /epsilon/hal/register-defaults`
  - `GET /epsilon/hal/interfaces`
  - `GET /epsilon/diagnostics/{device_id}`
  - `POST /epsilon/recovery/{device_id}`
  - `POST /epsilon/firmware/summary`
- Omega (Olympus):
  - `POST /omega/marketplace/plugins`
  - `GET /omega/marketplace/plugins`
  - `POST /omega/collaboration/plan`
  - `POST /omega/distributed/nodes/{node_id}`
  - `GET /omega/distributed/nodes`
  - `POST /omega/policy/grant`
  - `GET /omega/policy/check`
  - `GET /omega/public-apis`
  - `GET /dashboard` — engineering dashboard
  - `GET /omega/dashboard/{section}` — dashboard JSON API

## Phase Alpha freeze checkpoint

- Tag: `v0.1.0-alpha`
- Codename: `Genesis`
- Status: `COMPLETE`

This tag is the formal architectural freeze for the Phase Alpha foundation.
All subsequent work should be tracked as post-Alpha milestones.

## Project layout

```
prometheus/
├── contracts/      # platform interfaces (plugin/device/agent/memory/scheduler/event bus)
├── core/           # config, logging, database, scheduler, bootstrap container wiring
├── services/       # internal APIs/orchestration services + event handlers
├── implementations/# concrete wiring for platform components
├── plugins/        # plugin SDK + installed plugins
├── agents/         # agent SDK + registered agents
├── memory/         # long-term memory store
├── reasoning/      # reasoning pipeline + compatibility reasoning API
├── knowledge/      # graph, ontology, provenance, learning, query engine
├── delta/          # digital engineering lab + time/scenario engines
├── epsilon/        # HAL, diagnostics, firmware knowledge, recovery planning
├── hardware/       # HAL interfaces, drivers, sessions, diagnostics, recovery
├── firmware/       # firmware metadata, partitions, compatibility, parser
├── security/       # authorization, permissions, auditing, integrity
├── sdk/            # plugin SDK (interfaces, decorators, lifecycle, testing)
├── omega/          # marketplace, policy, distributed runtime, public API catalog
├── agents/         # multi-agent coordination (coordinator, planner, consensus)
├── distributed/    # multi-node runtime (node registry, sync, runtime)
├── policy/         # policy engine (authorization, permissions, rules, audit)
├── marketplace/    # repositories (plugins, capabilities, drivers, agents)
├── enterprise/     # multi-tenancy (orgs, projects, users, teams, roles)
├── runtime_management/ # resource, memory, lifecycle management
├── dashboard/      # unified engineering dashboard (JSON API)
├── backend/        # FastAPI app — the local API
├── web/            # Vite + TypeScript engineering workstation SPA
├── tests/          # pytest coverage for managers/stores/bootstrap/happy path
└── requirements.txt
```
