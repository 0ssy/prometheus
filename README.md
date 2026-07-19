# Prometheus Platform

Prometheus is a local-first engineering platform with:

- Python + FastAPI backend
- Desktop-style web workspace
- Plugin and agent extensibility
- Knowledge, simulation, and hardware capabilities

---

## Platform status

**v1.0 foundation is frozen.**

Core platform changes should be limited to:

1. bug fixes, or
2. major architectural improvements.

New value should be added as capabilities built on top of the platform.

---

## One README, two paths

- **I am a user** -> [User guide](#user-guide)
- **I am a developer** -> [Developer guide](#developer-guide)

---

## User guide

### Requirements

- Python 3.11+
- pip

### Install

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt
```

### Start Prometheus

```bash
python prometheus.py
```

### Open it

- Dashboard: <http://127.0.0.1:8000/dashboard>
- API docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/health>

### Most-used commands

```bash
python prometheus.py --server
python prometheus.py --terminal
python prometheus.py --developer
python prometheus.py --safe-mode

python prometheus.py status
python prometheus.py demo
python prometheus.py test
python prometheus.py extensions
```

### Hardware capability commands

```bash
python prometheus.py usb -h
python prometheus.py serial -h
```

---

## Developer guide

### 30-second repo map

- `core/` -> runtime foundations (boot, config, container, logging)
- `backend/` -> API endpoints
- `services/` -> orchestration and business logic
- `hardware/` -> hardware capabilities (USB, Serial, etc.)
- `firmware/` -> firmware parsing/metadata/compatibility
- `knowledge/`, `memory/`, `simulation/` -> intelligence layers
- `agents/`, `plugins/`, `sdk/` -> extension surfaces
- `dashboard/` -> dashboard data and composition
- `omega/` -> compatibility/orchestration facade
- `web/` + `src-tauri/` -> UI and native desktop packaging

If you add a new capability (for example Bluetooth), start in `hardware/`,
then expose integration through `services/` and `backend/`.

### Local development

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

### Frontend (`web/`)

```bash
cd web
npm install
npm run typecheck
npm run lint
npm run build
```

### Rust workspace (`crates/`)

Rust crates are managed by the root `Cargo.toml` workspace.

### Native desktop (`src-tauri/`)

```bash
cd src-tauri
cargo tauri dev
cargo tauri build
```

---

## Extending Prometheus

### Scaffold a plugin/agent/driver

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

## API quick list

- `GET /health`
- `GET /status`
- `GET /stats`
- `GET /dashboard`
- `GET /omega/dashboard/{section}`
- `POST /assistant`
- `POST /commands`

For complete API contracts, use `/docs` on a running instance.

---

## Current direction

The next major expansion is **hardware platform capabilities** (HAL-first),
followed by higher-level engineering applications that reuse those capabilities
across Assistant, SDK, plugins, and automation workflows.
