# Prometheus Platform

Prometheus is a local-first engineering platform with:

- Python + FastAPI backend
- Rust-first hardware HAL (`crates/hal-core`)
- Desktop-style web workspace
- Plugin and agent extensibility
- Knowledge, simulation, and hardware capabilities

---

## Platform status

**v1.0 foundation is frozen.**

Core platform changes should be limited to:

1. bug fixes, or
2. major architectural improvements.

New value is added as capabilities built on top of the platform.

---

## Quick start (end users)

### One-click install

| OS | Command |
|---|---|
| **Windows** | `prome.bat install` |
| **macOS / Linux** | `python prome.py install` |

`install` creates the Python venv, installs dependencies, checks for Rust/cargo,
and builds the native HAL crate (`hal-core`).

### Run

```bash
# Windows
prome.bat run

# macOS / Linux
python prome.py run
```

### Open

- Dashboard: <http://127.0.0.1:8000/dashboard>
- API docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/health>

### Other launcher commands

```bash
prome.py status   # show Python, venv, cargo, hal-core paths
prome.py update   # reinstall + rebuild after a pull
```

### Native desktop packaging

A Tauri-based desktop wrapper lives in `src-tauri/`:

```bash
cd src-tauri
cargo tauri build
```

Windows builds produce a self-contained `.exe` in `src-tauri/target/release/bundle/`.

A PyInstaller spec (`prometheus.spec`) is also included for pure-Python
distribution if you prefer a `prometheus.exe` without Tauri.

---

## Implemented capabilities

| Capability | Transport | Primary Language | Status |
|---|---|---|---|
| USB | `usb:` | Rust + Python | Implemented |
| Serial / UART | `serial:` / `COM*` / `/dev/tty*` | Rust + Python | Implemented |
| ADB | `adb:` | Rust + Python | Implemented |
| Fastboot | `fastboot:` | Rust + Python | Implemented |
| GPIO | `gpio:` | Rust | Implemented |
| SPI | `spi:` | Rust | Implemented |
| I²C | `i2c:` | Rust | Implemented |
| CAN Bus | `can:` / `vcan:` | Rust | Implemented |
| Bluetooth / BLE | `ble:` / `bt:` | Rust | Implemented |
| JTAG | `jtag:` | Rust + C | Implemented |
| SWD | `swd:` | Rust + C | Implemented |
| HID | `hid:` / `/dev/hidraw*` | Rust | Implemented |
| DFU | `dfu:` | Rust | Implemented |
| Recovery | `recovery:` | Rust | Implemented |
| Network | `tcp:` / `udp:` / `http:` | Rust | Implemented |

Platform transport support is exposed through `crates/hal-core` with
feature-gated real backends (`usb-real`, `serial-real`, `adb-real`,
`fastboot-real`, `hid-real`, `dfu-real`, `swd-real`, `recovery-real`).
Unused transports fall back to deterministic simulation by default.

---

## One README, two paths

- **I am a user** -> [User guide](#user-guide)
- **I am a developer** -> [Developer guide](#developer-guide)

---

## User guide

### Requirements

- Python 3.11+
- pip
- Rust toolchain (for `hal-core` and native HAL features)

### Install (manual)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt
python prometheus.py --server
```

### Hardware capability commands

```bash
python prometheus.py usb -h
python prometheus.py serial -h
python prometheus.py hid -h
```

---

## Developer guide

### 30-second repo map

- `core/` -> runtime foundations (boot, config, container, logging)
- `backend/` -> API endpoints
- `services/` -> orchestration and business logic
- `hardware/` -> hardware capabilities (USB, Serial, HAL, recovery, drivers)
- `firmware/` -> firmware parsing/metadata/compatibility
- `knowledge/`, `memory/`, `simulation/` -> intelligence layers
- `agents/`, `plugins/`, `sdk/` -> extension surfaces
- `dashboard/` -> dashboard data and composition
- `omega/` -> compatibility/orchestration facade
- `web/` + `src-tauri/` -> UI and native desktop packaging
- `crates/` -> Rust workspace (HAL core, Titan, Aether, SDK, policy, etc.)

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
cargo test -p hal-core --lib
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

```bash
# check all crates
cargo check --workspace

# test HAL core
cargo test -p hal-core --lib
```

### Native desktop (`src-tauri/`)

```bash
cd src-tauri
cargo tauri dev
cargo tauri build
```

---

## Packaging for end users

| Method | Output | Notes |
|---|---|---|
| `prome.bat install` | venv + deps on user machine | Use for dev / portable |
| `src-tauri` build | `prometheus.exe` | Best distribution artifact |
| `pyinstaller` (`prometheus.spec`) | `prometheus.exe` | Pure-Python bundle |

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
