# Prometheus Platform

Prometheus is a local-first engineering platform that combines:

- a Python/FastAPI backend,
- a desktop-style web workspace,
- plugin + agent extensibility,
- knowledge, simulation, and hardware-oriented services.

---

## Platform status

**v1.0 foundation is frozen.**

That means platform core work is now limited to:

1. bug fixes, or
2. breaking architectural improvements.

New value should be added as capabilities on top of the platform.

---

## Start here

- **I want to use Prometheus** -> [User guide](#user-guide)
- **I want to build on Prometheus** -> [Developer guide](#developer-guide)

---

## User guide

### 1) Requirements

- Python 3.11+
- pip

### 2) Install and run

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt
python prometheus.py
```

By default this starts the backend and opens the dashboard.

### 3) Open the product

- Dashboard: <http://127.0.0.1:8000/dashboard>
- API docs: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

### 4) Common commands

```bash
python prometheus.py --server       # API only (no browser)
python prometheus.py --terminal     # terminal mode
python prometheus.py --safe-mode    # minimal services
python prometheus.py status         # platform status banner
python prometheus.py demo           # happy-path demo
python prometheus.py test           # run tests
python prometheus.py extensions     # list SDK extension packages
```

### 5) What users get

- Desktop workspace + terminal
- Dashboard and API
- Plugin system
- Agent runtime
- Knowledge and simulation surfaces
- Hardware-oriented services and diagnostics endpoints

---

## Developer guide

### Architecture at a glance

Prometheus is organized around stable service contracts and a bootstrapped container:

- **API runtime**: `backend/main.py`
- **Bootstrap/wiring**: `core/bootstrap.py`
- **Service container**: `core/container.py`
- **Orchestration services**: `services/`
- **Core subsystems**:
  - `agents/`
  - `distributed/`
  - `policy/`
  - `marketplace/`
  - `enterprise/`
  - `runtime_management/`
  - `dashboard/`

### Local development setup

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt
python prometheus.py --server
```

### Run tests

```bash
pytest -q
```

### Frontend workspace (`web/`)

```bash
cd web
npm install
npm run typecheck
npm run lint
npm run build
```

### Rust workspace (`crates/`)

The repository also includes Rust crates (HAL/runtime/Titan/distributed/etc.) managed via the root `Cargo.toml` workspace.

### Native desktop build (Tauri)

```bash
cd src-tauri
cargo tauri dev
cargo tauri build
```

Use this path for native desktop packaging/distribution.

---

## Extending the platform

### Plugin/agent scaffolding

```bash
python prometheus.py new plugin my_plugin
python prometheus.py new agent my_agent
python prometheus.py new driver my_driver
```

### Package and verify

```bash
python prometheus.py pack <path>
python prometheus.py verify <path-to-zip>
```

---

## API highlights

- `GET /health`
- `GET /status`
- `GET /stats`
- `GET /dashboard`
- `GET /omega/dashboard/{section}`
- `POST /assistant`
- `POST /commands`

For full contract details, use `/docs` in a running instance.

---

## Current direction

The next major expansion is **Hardware Platform capabilities** (HAL-first), then higher-level engineering applications that reuse those capabilities across Assistant, SDK, plugins, and automation workflows.
