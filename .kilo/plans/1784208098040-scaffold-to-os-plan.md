# PROMETHEUS SCAFFOLD-TO-OS IMPLEMENTATION PLAN

## CONSTRAINT
- Languages per phase are fixed by the roadmap. Do not substitute.
- Do not rewrite existing Python core. Extend it.
- Each phase must be verifiable before the next begins.

---

## PHASE 0 — SCAFFOLD REPAIR (unblock everything)

**Goal:** Make the repo green and structurally sound so every subsequent phase has a stable base.

### 0.1 Lint Repair (62 errors)
After `ruff check . --fix` (auto-resolved 131 issues), **62 errors remain**:
- **E402 (50):** Module-level imports not at top of file.
  - `backend/main.py`: intentional lazy imports to avoid circular deps. Add `# noqa: E402` to those lines.
  - `devices/*.py` (6 files): deprecated shim. Either migrate to `hardware/` (see 0.2) or add `# noqa: E402`.
  - `omega/*.py` (14 files), `prometheus.py`, `services/bootstrap.py`: real style violations. Move imports to top or convert to lazy imports with `# noqa: E402`.
- **F841 (6):** Unused local variables. Remove assignments.
- **F811 (2):** Redefinition of unused variable. Remove duplicate.
- **E731 (1):** Lambda assigned to variable. Convert to `def`.
- **F402 (1), F405 (1), F821 (1):** Shadowed/undefined names. Fix definitions.
- **Validation:** `ruff check .` returns 0 errors.

### 0.2 devices → hardware Migration
`devices/` is deprecated (emits `DeprecationWarning` on import) but **14 files** still import from it:
- `implementations/platform_components.py` — **core wiring**; must migrate to `hardware.compat.adapter.DeviceRegistryAdapter`.
- `tests/test_epsilon_integration.py`, `tests/test_epsilon_service.py`, `tests/test_platform_service.py`, `tests/test_device_registry.py`
- `hardware/compat/adapter.py` (wraps legacy, should unwrap)
- `digital_twin/twin.py`
- `engineering/device_simulator.py`

**Action:**
1. Migrate `implementations/platform_components.py` to import `DeviceRegistryAdapter` from `hardware.compat.adapter`.
2. Update all 14 importers to use `hardware/` equivalents.
3. Remove `devices/` shim once no importers remain (or keep as empty re-export if external deps exist).
- **Validation:** `python -W error -c "import devices"` fails (shim removed) OR zero `DeprecationWarning` from `devices` imports.

### 0.3 Rust-Python Bridge (selective, not blanket)
**Reality:** Only 3 of 5 crates have `pyo3` optional dep (`hal-core`, `aether-runtime`, `tensor-engine`). Only `titan-tokenizer` is consumed by Python (`titan/tokenizer.py`), and it uses a pure-Python fallback. No `maturin` config, no `build.rs`, no compiled extensions exist in the repo.

**Action:**
1. Add `maturin` + per-crate `pyproject.toml` for `hal-core`, `aether-runtime`, `tensor-engine` only.
2. Add `scripts/build_rust_extensions.ps1` / `.sh` that builds these 3 crates with `--features python`.
3. Wire `hardware/flash_service.py` to try `hal_core` import, fall back to `cryptography`.
4. Wire `aether/runtime.py` to try `aether_runtime` import, fall back to Python.
5. Leave `ai-runtime` and `titan-tokenizer` as Rust-only (served via Tauri / optional pip install).
- **Validation:** `cargo build --workspace` succeeds. `scripts/build_rust_extensions.ps1` produces `.pyd` files. Python falls back gracefully when extensions are absent.

### 0.4 Frontend/Backend API Alignment
**Reality:** Backend has ~90 endpoints in `backend/main.py` + ~10 in `backend/phase_endpoints.py`. Frontend `web/src/api/client.ts` has ~45 methods. Many backend endpoints have no frontend consumer; many frontend clients have no backend endpoint.

**Action:**
1. Audit `client.ts` vs `main.py` + `phase_endpoints.py`.
2. Add missing high-priority client methods: `/system/baseline`, `/system/baseline/refresh`, `/system/jobs`, `/system/resources`, `/system/services`, `/system/native-runtime`, `/events`, `/commands`, `/capabilities/history`, `/engineering/modules`, `/titan/modules`, `/omega/distributed/nodes`, `/omega/marketplace/plugins` (POST), `/ownership` (GET), `/ownership/{id}` (DELETE), `/devices/{id}/disconnect`, `/devices/{id}/write`, `/devices/serial`.
3. Do NOT add frontend clients for internal-only endpoints (e.g., `/omega/agents/consensus`, `/omega/policy/grant`) unless a TS app needs them.
- **Validation:** Every `client.ts` method resolves to an existing backend route (no 404 on method call).

### 0.5 Go / C++ Hygiene
- **Go:** Remove committed binaries `go/*.exe` from git (they are build artifacts). Add `.gitignore` entry for `go/*.exe`.
- **C++:** `cpp/build/` contains CMake build artifacts. Add `.gitignore` entry for `cpp/build/`.
- **Validation:** `git status` shows no build artifacts as tracked changes.

### 0.6 Test Baseline
- **Validation:** `pytest` passes (343), `cargo test --workspace` passes (43), `npm run build` passes.

---

## PHASE 1 — ENGINEERING OS
**Languages:** Python, SQL, TypeScript/React

**Existing:** Bootstrap (58 services), DB, plugins, agents, kernel, scheduler, 22 TS apps, FastAPI backend with ~100 endpoints.

**Build:**
1. **Python:** `test_plugin_lifecycle.py` already exists. Add `PluginManager.unregister()` + `list_plugins()` to `plugins/manager.py` if missing. Verify lifecycle events fire on register/unregister.
2. **SQL:** `Metric`, `AuditLog`, `PluginRun` tables already imported in `core/database.py` `init_db()`. Verify they are created and accessible.
3. **TypeScript:** Complete `WindowManager.ts` (minimize, maximize, cascade, tab-dock). `Terminal.ts` already exists — add command registry (`help`, `show devices`, `run simulation`, `status`). `FilesApp.ts` already exists — add directory tree + file viewer. `SettingsApp.ts` already exists — add persisted prefs (`localStorage` + `/api/settings`).
4. **React/TS:** `ActivityApp.ts`, `AgentsApp.ts`, `HardwareApp.ts` already exist — flesh out with real data binding (not mocked static HTML).
- **Validation:** `pytest` + `ruff check` + `npm run build` green. Desktop.ts opens all dock apps without console errors. `test_plugin_lifecycle.py` passes.

---

## PHASE 2 — COMPLETE HARDWARE PLATFORM
**Languages:** Rust, C, C++, Zig 

**Existing:** `hal-core` crate (4 transports, Ed25519, conformance, PyO3), `hardware/drivers/` (17 Python drivers), C `usb.c`/`kernels.c`, Python `FlashService`, `HALProtocolTest`/`FirmwareFlashLog` tables.

**Build:**
1. **Rust:** Extend `hal-core` `Transport` enum from 4 to all roadmap protocols: Serial, UART, I2C, SPI, CAN, LIN, JTAG, SWD, GPIO, PCIe, HID, Bluetooth, BLE, WiFi, Ethernet, NFC, RFID, LoRa, Zigbee, Z-Wave, MQTT, Modbus, OPC-UA, BACnet, RS232, RS485. Implement `SimulatedHal` probes for each. Add `run_conformance` matrix test (target: 12+ Rust tests).
2. **C:** Add `cpp/hardware/drivers/serial.c`, `i2c.c`, `spi.c`, `gpio.c` with deterministic probe stubs. Add matching headers. Verify CMake builds `prometheus_usb` + new drivers.
3. **C++:** Add `cpp/hardware/drivers/usb.hpp` and thin C++ wrapper around C USB driver.
4. **Zig:** Defer to spike. Document `zig/hal/bridge.zig` concept but do not implement unless Zig target is identified.
5. **Python:** Complete `hardware/session.py` (`DeviceSessionManager`), `hardware/diagnostics.py` (`HardwareDiagnostics`), `hardware/recovery.py` (`HardwareRecovery`). Wire `FlashService` to use `hal-core` PyO3 bindings when available; keep `cryptography` fallback.
- **Validation:** Rust tests pass (12+). `cpp/hardware/drivers/*.c` compile with CMake. Python `test_hardware_hal.py` passes. No `DeprecationWarning` from `devices` imports.

---

## PHASE 3 — AETHER AI RUNTIME
**Languages:** Rust, C++, TypeScript

**Existing:** `ai-runtime` crate (8 providers, health, routing, context, tools), `aether-runtime` crate (router, dispatcher, context store), Python `aether/runtime.py` (Router, ToolDispatcher, ContextStore), TS `AssistantApp.ts`.

**Build:**
1. **Rust:** `ai-runtime` already has all providers. Add `AetherRuntime::route()` async wrapper for Python. Add `ToolDispatcher::with_backend()` for REST backend calls. Expose context engine snapshot via PyO3 in `aether-runtime` crate (already has `ContextStore`).
2. **C++:** Add `cpp/aether/context_engine.cpp` — simple vector-store mock with C ABI. Header: `cpp/aether/context_engine.h`.
3. **TypeScript:** Enhance `AssistantApp.ts` to call `/aether/route` and `/assistant` endpoints. Add streaming SSE support. Add chat history panel.
4. **Python:** Wire `AetherRuntime.select_provider()` to try `aether_runtime` Rust import, fall back to Python `Router`. Ensure tool dispatch calls Rust when available.
- **Validation:** Rust tests pass (30+). TS builds. `/aether/route` returns provider. `/assistant` returns response.

---

## PHASE 4 — ENGINEERING INTELLIGENCE
**Languages:** Rust, C++, TypeScript

**Existing:** `engineering/` Python modules (12 disciplines), `EngineeringIntelligence` confidence-gating, `EngineeringStudioApp.ts`, `engineering_reports`/`engineering_feedback` tables.

**Build:**
1. **Rust:** Add `crates/verification-engine` — trait `Verifier` with `verify_design()`, `verify_code()` returning confidence score. Expose to Python via PyO3.
2. **C++:** Add `cpp/engineering/sim_kernels.cpp` — deterministic physics/math stubs (`sim_step()`). Header-only interface.
3. **TypeScript:** Enhance `EngineeringStudioApp.ts` with approval queue UI (approve/reject buttons wired to `/engineering/suggestions/{id}/approve`), confidence meter, report list.
4. **Python:** Add `EngineeringIntelligence.feedback_kpis()` — track approval rate, avg confidence, time-to-approval.
- **Validation:** Rust tests pass. TS builds. POST `/engineering/suggestions` returns report; GET returns list; POST approve changes status.

---

## PHASE 5 — TITAN AI PLATFORM
**Languages:** Python, Rust, C++, CUDA 

**Existing:** `titan/` Python service, `titan-tokenizer` crate (4 Rust tests), `Dataset`/`Model` tables, `TitanGovernance`, Python fallback tokenizer.

**Build:**
1. **Python:** `finetune.py` calls `transformers`/`deepspeed` if installed; otherwise logs "stub". Add `evaluation.py` with perplexity/accuracy metrics. Add `quantization.py` (GGUF/ONNX stubs).
2. **Rust:** Extend `titan-tokenizer` with BPE/WordPiece trainers (in-memory). Add `crates/titan-embeddings` — embedding model trait (future ONNX runtime).
3. **C++:** Add `cpp/titan/inference.cpp` — C API for loading a GGUF-like tensor and running a forward pass (deterministic stub). Header: `cpp/titan/inference.h`.
4. **CUDA:** Add `crates/titan-cuda` with `CudaTensor` struct (feature-gated `cudarc`). Implement `cuda_matmul()` stub that panics with "CUDA not available" on non-CUDA builds. `cargo check --features cuda` must pass without GPU.
- **Validation:** Python tests pass. Rust tests pass (8+). C++ compiles. `cargo check --features cuda` succeeds.

---

## PHASE 6 — HIGH PERFORMANCE ENGINE
**Languages:** Rust, C++, CUDA 

**Existing:** `tensor-engine` crate (add, dot, matmul, save/load), C `kernels.c` (matmul, add), `perf_metrics` table.

**Build:**
1. **Rust:** Add SIMD to `tensor-engine` via `std::simd` (Rust 1.77+) for element-wise add/dot. Add `Tensor::mmap()` using `memmap2` crate. Add `PerfRegistry` with 3% regression guard (snapshot baseline, compare on test run, write to `perf_metrics`).
2. **C++:** Extend `cpp/tensor/kernels.c` to `cpp/tensor/kernels.cpp` with blocked matmul, vectorized add (AVX2/NEON via compiler intrinsics), `tensor_save_mmap()`.
3. **CUDA:** Add `crates/tensor-cuda` with `CudaTensor` struct (feature-gated `cudarc`). `cuda_matmul()` stub panics without GPU. Document kernel launch parameters.
- **Validation:** Rust tests pass (10+). C++ compiles. `perf_metrics` table populated on test run. `cargo check --features cuda` passes.

---

## PHASE 7 — DISTRIBUTED COMPUTING
**Languages:** Rust, Go, C++

**Existing:** Python `DistributedScheduler` (cluster submit + local fallback + recovery), Go `controlplane` + `worker` (stdlib HTTP, prebuilt `.exe`), `distributed_tasks`/`distributed_recoveries` tables.

**Build:**
1. **Rust:** Add `crates/distributed-runtime` — `Task`, `Node`, `WorkStealingQueue` traits. Expose Python extension for local work-stealing when Go cluster is down.
2. **Go:** Replace stdlib HTTP with `gRPC` (protobuf definitions in `go/proto/`). Ensure `go run ./cmd/controlplane` and `go run ./cmd/worker` work with protobuf. Add billing service gRPC endpoint.
3. **C++:** Add `cpp/distributed/worker_bridge.cpp` — C API for C++ applications to submit tasks to Go control plane via gRPC (or HTTP fallback).
4. **Python:** Enhance `DistributedScheduler` to use Rust extension for local work-stealing when Go cluster is unavailable.
- **Validation:** Rust tests pass. `go build ./...` succeeds. Python tests pass. End-to-end: Python submits task → Go worker executes → recovery logged.

---

## PHASE 8 — CLOUD PLATFORM
**Languages:** Rust, TypeScript, Go

**Existing:** `enterprise/models.py` (tenants, roles, users, permissions, usage_events, invoices), Go `billing` service (stdlib HTTP), `StatusApp.ts`, P8 endpoints in `phase_endpoints.py`.

**Build:**
1. **Rust:** Add `crates/auth-gateway` — JWT validation, tenant-scoped RBAC middleware. Expose as standalone sidecar or via PyO3.
2. **Go:** Enhance `cmd/billing` to read from `usage_events` via SQLite (or accept gRPC ingest). Add `/tenant/{id}/invoice` endpoint.
3. **TypeScript:** Rewrite `StatusApp.ts` into full `CloudApp.ts` — tenant switcher, user management, role editor, invoice viewer, usage charts.
4. **Python:** `AuthService` + `BillingService` already exist in `enterprise/cloud.py`. Add ≤0.5% discrepancy KPI test.
- **Validation:** Rust tests pass. `go build ./...` succeeds. TS builds. SQL tables populated. `/billing/invoice` returns correct total.

---

## PHASE 9 — PROMETHEUS SDK
**Languages:** Rust, TypeScript, C++, Python

**Existing:** Rust crates, Python `sdk_versions` table, `SdkRegistry`, C++ `CMakeLists.txt` + compiled `prometheus_tensor.lib`/`prometheus_usb.lib`.

**Build:**
1. **Rust:** Publish `hal-core`, `aether-runtime`, `tensor-engine` with semver `Cargo.toml`. Add `crates/sdk-core` re-exporting all three with unified feature matrix.
2. **TypeScript:** Create `web/src/sdk/` — `PrometheusClient` class wrapping FastAPI REST API. Scaffold `package.json`, `tsconfig.json`, build script for `prometheus-sdk` npm package.
3. **C++:** Complete `cpp/sdk/` header-only wrappers for HAL, tensor, and Aether context. Add install targets to `CMakeLists.txt`.
4. **Python:** Add `sdk/` package with `PluginSDK`, `AgentSDK`, `HardwareSDK` classes. Register versions in `sdk_versions` table on install.
- **Validation:** Rust crates build. TS SDK type-checks. C++ `cmake` config works. Python SDK can register a plugin/agent/driver.

---

## PHASE 10 — ENGINEERING ECOSYSTEM
**Languages:** Python, TypeScript

**Existing:** `marketplace/models.py`, `MarketplaceGovernance`, `GovernanceApp.ts`, P10 endpoints in `phase_endpoints.py`.

**Build:**
1. **Python:** `marketplace_approvals` table + `MarketplaceGovernance` quality-gated review already exist. Add quality gates (lint, test, security scan). Add `labs/` service stubs for each studio domain.
2. **TypeScript:** Create 15 studio apps in `web/src/apps/`:
   - `RoboticsStudioApp.ts`, `FirmwareStudioApp.ts`, `PCBStudioApp.ts`, `CADStudioApp.ts`, `PLCStudioApp.ts`, `DroneStudioApp.ts`, `AutomotiveStudioApp.ts`, `SecurityLabApp.ts`, `ReverseEngLabApp.ts`, `AILabApp.ts`, `VisionLabApp.ts`, `AudioLabApp.ts`, `NetworkingLabApp.ts`, `CloudLabApp.ts`, `EmbeddedLabApp.ts`.
   - Each mounts a domain-specific panel (mocked data, wired to future backend).
3. **Dock integration:** Register all 15 apps in `web/src/os/Desktop.ts` `APPS` and `DOCK_KEYS`.
- **Validation:** TS builds (all 15 apps mountable from Dock). `GovernanceApp.ts` shows approval queue. Python tests for marketplace governance pass.

---

## PHASE 11 — PROMETHEUS OS
**Languages:** Python, TypeScript, Bash/PowerShell, SQL

**Existing:** `EnterpriseWorkflowRunner`, `EnterpriseWorkflow` model, `OSApp.ts` (47-line shell), `scripts/backup.py`, `scripts/restore.py`, `scripts/dr_failover.sh`, Rust workspace root.

**Build:**
1. **TypeScript:** Rewrite `OSApp.ts` into full desktop shell: kernel health widget, subsystem status grid, resource bars, live log tail, app launcher with search, multi-window tiling.
2. **Python:** Complete `EnterpriseWorkflowRunner` E2E steps: `connect` → `inspect` → `simulate` → `recover` → `deploy`. Add isolation (each step runs in a transaction; failures don't poison subsequent steps).
3. **SQL:** Ensure `enterprise_workflows` table has indexes on `device_id`, `success`, `created_at`.
4. **Bash/PowerShell:** Add `scripts/restore.ps1`, `scripts/dr_failover.ps1`, `scripts/backup.ps1`. Ensure cross-platform parity with existing `.sh`/`.py` scripts.
5. **Rust:** Root `Cargo.toml` workspace already exists. Document that `src-tauri` is the OS shell; do NOT add `crates/os-shell` unless Tauri commands need a dedicated Rust bridge.
- **Validation:** `test_enterprise_workflow.py` passes (success rate 100%). TS builds. `scripts/dr_failover.sh` runs end-to-end against test DB. `pytest` + `cargo test` + `npm run build` + `ruff check` all green.

---

## EXECUTION ORDER SUMMARY

| Order | Phase | Focus | Gate |
|-------|-------|-------|------|
| 0 | Scaffold Repair | ruff (62→0), devices→hardware migration, Rust-Python bridge, API alignment, git hygiene | All green |
| 1 | P1 Engineering OS | Python/SQL/TS desktop + plugin lifecycle | pytest 343+ |
| 2 | P2 Hardware | Rust/C/C++ transports + flashing + diagnostics | cargo test 12+ |
| 3 | P3 Aether | Rust/C++/TS AI runtime wiring + assistant | pytest + cargo + build |
| 4 | P4 Engineering | Rust/C++/TS verification + approval UI | pytest + cargo + build |
| 5 | P5 Titan | Python/Rust/C++ tokenizer/embeddings + CUDA stubs | pytest + cargo + cmake |
| 6 | P6 HPC | Rust/C++ tensor engine + SIMD + mmap | pytest + cargo + cmake |
| 7 | P7 Distributed | Rust/Go/C++ cluster + gRPC + recovery | pytest + go build |
| 8 | P8 Cloud | Rust/TS/Go tenant + billing + status UI | pytest + cargo + go build |
| 9 | P9 SDK | Rust/TS/C++/Python SDK publish | cargo + tsc + cmake + pytest |
| 10 | P10 Ecosystem | Python/TS 15 studios + governance | pytest + build |
| 11 | P11 OS | Python/TS/Bash/SQL desktop + DR | pytest + cargo + build + scripts |

---

## OPEN QUESTIONS (resolved)

1. **Rust-Python bridge:** `maturin` for `hal-core`, `aether-runtime`, `tensor-engine` only. `ai-runtime` and `titan-tokenizer` remain Rust-only (Tauri / optional pip).
2. **Go toolchain:** Add Go install docs + `go build` to CI. P7 implemented locally where Go exists; sandbox runs Python tests only.
3. **CUDA:** Stubs with feature guards. `cargo check --features cuda` passes without GPU. No kernels until hardware present.
4. **Tauri/NSIS:** Document existing `src-tauri/README.md` + add GitHub Actions workflow stub. Do not run in sandbox.
5. **Zig:** Deferred. Document concept; implement only if embedded Zig target is identified.
6. **devices vs hardware:** Migrate all 14 importers to `hardware/`. Remove `devices/` shim once migration is complete. Keep backward-compatible re-exports only if external packages depend on them.
7. **E402 violations:** 50 errors. 30+ are intentional lazy imports in `backend/main.py` + `devices/` shim + `omega/`. Add `# noqa: E402` to intentional cases. Fix remaining ~20 real violations in `omega/`, `prometheus.py`, `services/bootstrap.py`.
