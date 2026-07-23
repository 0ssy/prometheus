# Plan: C++ Platform Migration — Rust Elimination + Python Bridge + Doc Consistency

## Goal
Make the codebase consistent with the documented strategy: C++ first for Platform capabilities, C++ + CUDA for Titan, Python for AI research. Eliminate all runtime dependencies on Rust for Platform code.

## Current State
- C++ HAL transports implemented and building: 29 libraries under `build/hal/Release/`
- Python hardware layer still imports `hal_core` Rust module at runtime
- 10 stale Platform Rust crates in `crates/` (~60 `.rs` files)
- ~100 Rust references in docs/plans

## Proposed Execution Order

### Phase 1: Python→C++ Bridge (critical path)
**What:** Replace `import hal_core` in Python with a ctypes-based bridge to the C HAL.

**Why ctypes:** The C++ HAL already exposes `extern "C"` functions in `.dll`/`.lib` form on Windows and `.so` on Linux. ctypes needs no extra build toolchain, no PyO3, no Rust. It can load `build/Release/hal_core.dll` (or a future unified `prom_hal.dll`) directly from Python.

**Files to change:**
- `hardware/usb/manager.py` — stop importing `hal_core`, call `ctypes.CDLL("prom_hal_usb")` + `prom_usb_enumerate`
- `hardware/serial/manager.py` — same pattern, `prom_serial_*`
- `hardware/flash_service.py` — call `prom_verify_signature` equivalent (C++ Ed25519)
- `prometheus_cli/scaffold.py` — same if it imports hal_core
- `prome.py` — check for CMake build output instead of cargo

**Residual:** `crates/hal-core/src/lib.rs` PyO3 module is no longer needed once Python calls ctypes. Keep the Rust crate file until bridge is validated, then remove.

### Phase 2: Remove Stale Rust Crates
**What:** Delete or move `crates/` subdirectories that are NOT Titan/AI.

**Keep:**
- `crates/titan-engine/` — CUDA kernels
- `crates/titan-core/` — LLM inference types/tokenizer
- `crates/tensor-engine/` — tensor math with CUDA backend
- `crates/aether-runtime/` — Python AI runtime (mostly Python, some Rust is fine)

**Remove to graveyard:**
- `crates/hal-core/` → superseded by `cpp/hal/`
- `crates/sdk-core/` → migrate to C++ if needed, otherwise graveyard
- `crates/sdk-cli/` → same
- `crates/prometheus-kernel/` → same
- `crates/distributed/` → Go owns distributed now per roadmap
- `crates/cloud-core/` → Python/Go
- `crates/enterprise/` → Python
- `crates/marketplace/` → Python
- `crates/policy/` → Python
- `crates/runtime_management/` → Python

**Also remove:** root `Cargo.toml` if it only lists these crates.

### Phase 3: CMake Defaults Fix
**What:** Change `BUILD_HAL_SPI`, `BUILD_HAL_I2C`, `BUILD_HAL_CAN`, `BUILD_HAL_JTAG` from `OFF` to `ON` so all "implemented" transports build by default.

**Why:** README and ADR list them as implemented, but `cmake -B build -S cpp` won't build them without manual flag toggling.

### Phase 4: Documentation Cleanup
**What:** Update or accept drift for each Rust reference.

**Scope A — Update to C++:**
- `README.md` ✓ (already done)
- `ARCHITECTURE_DECISION_LOG.md` ✓ (already done)  
- `architecture/roadmap.md` ✓ (already done)
- `docs/capabilities/*.md` ✓ (already done)
- `KNOWN_LIMITATIONS.md` line 43 — replace "Rust ≥ 1.77" with "CMake + C++ compiler"
- `docs/architecture/sdk.md` lines 7, 73, 78 — replace Rust HAL Core section with C++ HAL
- `cpp/hardware/drivers/usb.c` line 4 — remove "Rust `hal-core`" comment
- `CHANGELOG.md` — update crate descriptions from "Rust" to "C++"

**Scope B — Accept as historical (no change needed):**
- `.kilo/plans/*.md` — these are historical plans, not current docs. Leave as-is.
- `docs/research/decision-records.md` DEC-006 — this is a record of a decision that was later reversed. Leave as historical record.
- `docs/release/rc1-checklist.md` — references past state. Leave as-is.

### Phase 5: Validation
- `cmake -B build -S cpp && cmake --build build --config Release` — must succeed with all transports ON
- Python smoke test: import `hardware.usb.manager` without `hal_core` import error
- Python smoke test: `ctypes.CDLL` can load a `prom_hal_*` library and call `prom_usb_enumerate`

## Key Design Decision — RESOLVED

**Python→C++ bridge: ctypes chosen.**

Rationale confirmed by user: ctypes needs no extra toolchain, can load the already-built `prom_hal_*.dll`/`.so` directly, and is the fastest path to eliminating the Rust runtime dependency from Python.

Open question removed.
