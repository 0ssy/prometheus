# Changelog

All notable changes to Prometheus are documented in this file.

## [Unreleased] - RC1 Hardening

Stability, crash-recovery, and install/onboarding work that precedes the
`v1.0.0-rc1` tag. No new features — only reliability, packaging, and docs.

### Added
- Installer smoke test (`tests/test_installer_smoke.py`): verifies a clean
  install boots and serves `/health`, `/status`, `/docs`, and that a
  pre-existing corrupted DB still boots (quarantine + recreate).
- Self-contained desktop installer: `cargo tauri build` now bundles the frozen
  Python backend as a Tauri `externalBin` sidecar (`src-tauri/binaries/`, via
  `scripts/build_app_exe.py` + PyInstaller) and launches it from `src/lib.rs`
  with `tauri-plugin-shell`, so the installed app needs no system Python. See
  `src-tauri/README.md`.

### Fixed
- `/knowledge/graph` no longer loads the entire graph into memory: it is
  capped at `PROMETHEUS_GRAPH_NODE_LIMIT` / `PROMETHEUS_GRAPH_EDGE_LIMIT`
  (default 10000) and reports `truncated` / `truncated_total` so the UI can
  inform the user instead of locking the tab.
- Corrupted SQLite databases no longer block boot: `init_db()` quarantines
  the file to `<path>.corrupted.<timestamp>`, rebuilds the engine, and
  recreates a fresh schema, then publishes a `DatabaseCorruptedEvent`.
- `omega` `ResourceManager.to_dict()` no longer raises `AttributeError`:
  `_throttled` / `_throttle_reason` are initialized in `__init__`.
- Plugin failures are isolated: `PluginManager.run()` catches exceptions,
  logs them, publishes a `PluginErrorEvent`, and returns `{"error": ...}`
  instead of crashing the request. A `timeout` argument aborts hung
  plugins via a worker-thread-safe `ThreadPoolExecutor` (returns
  `{"error": "timeout"}`).

### Changed
- `requirements.txt`: added `httpx` (required by FastAPI's `TestClient`,
  used across the test suite) and `psutil` (real resource usage in
  `/system/resources` — previously silently zeroed when missing).
- Frontend (`web/src/apps/KnowledgeApp.ts`): the graph renderer clamps
  nodes/edges to the same cap before layout and shows a "+N more (capped)"
  indicator, so a larger-than-expected payload can't freeze the tab.
- `README.md`: added a Quickstart and corrected the install/verify steps;
  `tests/README.md` updated to the actual flat test layout.
- `prometheus.py` now imports the FastAPI app directly (`from backend.main import
  app`) instead of a string `uvicorn.run("backend.main:app", ...)` import, which
  is untraceable by PyInstaller — the backend is now freezable into a sidecar.

## [0.6.0-omega] - 2026-07-06

Codename: **Olympus**  
Status: **IN_PROGRESS**

### Added
- RC1 release hardening checklist: `docs/release/rc1-checklist.md`
- Plugin SDK (`sdk/plugin_sdk/`):
  - `interfaces.py`, `decorators.py`, `lifecycle.py`, `testing.py`, `examples/`
- Multi-Agent Coordination (`agents/`):
  - `coordinator.py`, `planner.py`, `consensus.py`, `delegation.py`
- Distributed Runtime (`distributed/`):
  - `node.py`, `runtime.py`, `sync.py`
- Policy Engine (`policy/`):
  - `authorization.py`, `permissions.py`, `rules.py`, `audit.py`
- Marketplace (`marketplace/`):
  - `plugin_repo.py`, `capability_repo.py`, `driver_repo.py`, `agent_repo.py`
- Enterprise Configuration (`enterprise/`):
  - `organizations.py`, `projects.py`, `users.py`, `teams.py`, `roles.py`
- Runtime Management (`runtime_management/`):
  - `resource_manager.py`, `memory_manager.py`, `lifecycle_manager.py`
- Engineering Dashboard (`dashboard/`):
  - `overview.py`, `devices.py`, `knowledge.py`, `simulation.py`, `firmware.py`, `diagnostics.py`, `recovery.py`, `agents.py`, `plugins.py`, `metrics.py`, `logs.py`, `policies.py`
- Omega service integration:
  - Updated `services/omega_service.py` to orchestrate all Omega components
  - Updated `core/bootstrap.py` to register Omega sub-services
  - Added Omega API endpoints in `backend/main.py`

### Architecture
- Platform now supports plugin SDK, multi-agent coordination, distributed runtime, policy engine, marketplace, enterprise configuration, runtime management, and unified dashboard.
- All hardware actions remain policy-aware and auditable.

## [0.5.0-epsilon] - 2026-07-06

Codename: **Hephaestus**  
Status: **IN_PROGRESS**

### Added
- Hardware Abstraction Layer (HAL):
  - `hardware/hal/interface.py`, `hardware/hal/manager.py`, `hardware/hal/registry.py`, `hardware/hal/capability_mapper.py`
- Driver framework:
  - `hardware/drivers/base.py`, `hardware/drivers/usb.py`, `hardware/drivers/adb.py`, `hardware/drivers/fastboot.py`, `hardware/drivers/network.py`, `hardware/drivers/virtual.py`
- Device Session Manager:
  - `hardware/session.py` with `DeviceSession` and `DeviceSessionManager`
- Hardware diagnostics engine:
  - `hardware/diagnostics.py` with `HardwareDiagnostics`
- Hardware recovery planner:
  - `hardware/recovery.py` with `HardwareRecovery`
- Hardware event pipeline:
  - `hardware/events.py` with `DeviceConnectedEvent`, `DeviceDisconnectedEvent`, `BatteryLowEvent`, `FirmwareDetectedEvent`, `DriverFailedEvent`, `SessionExpiredEvent`
- Firmware intelligence package:
  - `firmware/metadata.py`, `firmware/partitions.py`, `firmware/compatibility.py`, `firmware/parser.py`
- Security layer package:
  - `security/authorization.py`, `security/permissions.py`, `security/auditing.py`, `security/integrity.py`
- Epsilon service integration:
  - Updated `services/epsilon_service.py` to orchestrate HAL, sessions, diagnostics, recovery, firmware, and security
  - Updated `core/bootstrap.py` to wire Epsilon components
  - Added Epsilon API endpoints in `backend/main.py`

### Architecture
- Hardware never bypasses reasoning. All hardware actions flow through the HAL, are authorized, audited, and feed into the digital twin/knowledge graph.
- Recovery planning is separate from execution. Prometheus analyzes and recommends; execution remains an explicit, authorized step.

## [0.4.0-delta] - 2026-07-06

Codename: **Daedalus**  
Status: **COMPLETE**

### Added
- Delta digital engineering lab modules:
  - `delta/lab.py`, `delta/scenario_engine.py`, `delta/time_engine.py`
- Epsilon bridge scaffolding modules:
  - `epsilon/hal.py`, `epsilon/diagnostics.py`, `epsilon/recovery.py`, `epsilon/firmware.py`
- Omega ecosystem scaffolding modules:
  - `omega/ecosystem.py`
- New services and API endpoints for Delta/Epsilon/Omega progression:
  - `services/delta_service.py`
  - `services/epsilon_service.py`
  - `services/omega_service.py`

### Changed
- Bootstrap now registers `delta_service`, `epsilon_service`, and `omega_service`.
- Runtime version advanced to `0.4.0-delta`.
- Delta service now integrates with knowledge engine and digital twin:
  - `DeltaService` records simulation outcomes to knowledge graph
  - `DeltaService.build_twin()` materializes digital twins from knowledge graph facts
- Epsilon service now bridges to Delta digital twin:
  - `EpsilonService.diagnostics()` updates digital twin during hardware assessment
  - `EpsilonService.recovery_plan()` includes digital twin context
- Omega service now integrates with kernel permission system:
  - `OmegaService.grant_permission()` delegates to kernel `PermissionManager`
  - `OmegaService.plan_collaboration()` considers HAL interfaces from Epsilon

## [0.3.0-gamma] - 2026-07-06

Codename: **Helios**  
Status: **COMPLETE**

### Added
- Phase Gamma (Helios) knowledge layer:
  - `knowledge/graph.py`, `knowledge/node.py`, `knowledge/edge.py`
  - `knowledge/query.py`, `knowledge/ontology.py`
  - `knowledge/provenance.py`, `knowledge/learning.py`
  - `knowledge/engine.py`
- Knowledge graph persistence tables: nodes, edges, learning experiences.
- Gamma knowledge query endpoints:
  - `/gamma/knowledge/devices-supporting-recovery`
  - `/gamma/knowledge/simulations-failed`
  - `/gamma/knowledge/capabilities-never-executed`
  - `/gamma/knowledge/plugins-for-recommendation`
  - `/gamma/learning`
- Independent knowledge engine API shape:
  - `knowledge_engine.assert_fact(...)`
  - `knowledge_engine.query(...)`
  - `knowledge_engine.learn(...)`

### Changed
- Reasoning writes now project into the knowledge graph with provenance and confidence.
- Platform service now records:
  - device-to-capability relationships
  - simulation outcomes
  - capability execution evidence
  - learning experiences
- Core bootstrap now registers `knowledge_engine`.

### Architecture
- Introduced dedicated knowledge engine to isolate storage, ontology, query, and learning from other subsystems.
- Knowledge layer now supports direct container usage without importing reasoning/simulation/platform services.

### Known limitations
- Ontology is currently in-memory and seeded with starter taxonomy only.
- No automated migration system yet for existing SQLite databases.

## [0.2.0-beta] - 2026-07-06

### Added
- Capability framework (register/discover/authorize/execute/history)
- Digital-device service projection
- Simulation engine and reasoning pipeline
- Prometheus Core Kernel runtime
- Health and observability endpoints
- End-to-end Beta workflow endpoint

## [0.1.0-alpha] - 2026-07-06

### Added
- Foundation architecture:
  - bootstrap lifecycle
  - service container
  - event bus
  - plugin/agent frameworks
  - scheduler
  - API bootstrap
  - root runtime entrypoint
