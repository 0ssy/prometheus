# Prometheus Master Roadmap v3.0 — Implementation Plan

**Vision:** Prometheus is an **Engineering Intelligence Platform** — a desktop workspace running on Windows, Linux, and macOS via Tauri, unifying AI, hardware, knowledge, simulation, and engineering workflows.

**Non-goal:** Prometheus is NOT an operating system kernel. It runs on existing operating systems.

---

## Verified Toolchain (Windows dev box — 2026-07-16)

| Tool | Version | PATH entry |
|------|---------|------------|
| Rust | 1.97.0 | `C:\Users\josep\.cargo\bin` |
| Python | 3.11.9 | venv / system |
| Node.js | v24.18.0 | system |
| npm | 11.16.0 | system |
| TypeScript | via npm | system |
| MSVC `cl` | 19.44.x | `...\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64` |
| LLVM `clang/clang++` | installed | `C:\Program Files\LLVM\bin` |
| Go | 1.26.5 | `C:\Program Files\Go\bin` |
| Zig | 0.16.0 | WinGet package dir |
| CUDA `nvcc` | 13.3 | `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin` |
| maturin | 1.14.1 | Python311 Scripts |

**Note:** `gcc`/`g++` (MSYS2/MinGW) are  installed. Use `cl` or `clang++` for C/C++ compilation. All other roadmap languages are covered.

---
   
## Phase 0 — Foundation Cleanup

**Goal:** Align existing code with v3.0 naming and boundaries before building forward.

**Prereq:** All toolchains verified on PATH (see above). Phase 2, 5, and 6 are unblocked.

### Tasks

1. **Rust crate consolidation**
   - Merge `crates/ai-runtime` into `crates/aether-runtime` (they duplicate provider/routing logic).
   - Rename `crates/titan-tokenizer` to `crates/titan-core` and expand its scope.
   - Keep `crates/tensor-engine` and `crates/hal-core` as-is.
   - Update `Cargo.toml` workspace members and all `path` dependencies.

2. **Python entry-point refactor**
   - Replace `prometheus.py` monolithic CLI with `prometheus-cli/` package:
     - `commands/` — subcommands (status, demo, test, terminal, server)
     - `bootstrap/` — boot sequence
   - Preserve all existing subcommands and flags.

3. **Branding cleanup**
   - Replace "Engineering OS" / "Kernel" with "Engineering Intelligence Platform" in:
     - `prometheus.py` banner text
     - `backend/main.py` FastAPI title
     - `src-tauri/tauri.conf.json` product name
     - `web/src/boot/BootSequence.ts` terminology
     - README and docs

4. **API prefix normalization**
   - Current endpoints are flat (`/devices`, `/agents`, etc.).
   - Add versioned prefix `/api/v1/` to all FastAPI routes.
   - Maintain backward-compatible aliases at `/devices` etc. until P1 hardening.

### Validation

- `cargo test --workspace` passes
- `pytest -q` passes (smoke subset)
- Tauri dev build succeeds
- CLI `prometheus status` prints new branding

---

## Phase 1 — Platform Workspace (P1)

**Status:** Existing core functional. Hardening and desktop polish.

### Tasks

1. **Tauri desktop shell**
   - Replace current simple Tauri wrapper with a proper multi-panel workspace:
     - Left sidebar: navigation (Devices, Agents, Knowledge, Simulation, Settings)
     - Center: workspace panels
     - Bottom: integrated terminal (xterm.js + PTY bridge)
   - Window management: tabs, splits, minimize/restore.
   - Keep Python sidecar as the backend process.

2. **Backend service layer cleanup**
   - Split `services/platform_service.py` into focused services:
     - `DeviceService`
     - `AgentService`
     - `KnowledgeService`
     - `SimulationService`
   - Keep `PlatformService` as a facade for backward compatibility.

3. **Plugin manager hardening**
   - Implement capability-based sandboxing (seccomp on Linux, AppContainer on Windows, sandbox-exec on macOS).
   - Plugin signing and verification pipeline.
   - Hot-reload with state preservation.

4. **Agent manager stability**
   - Persistent agent state in SQLite.
   - Agent lifecycle: spawn, pause, resume, kill, restart.
   - Agent capability discovery and health reporting.

### Deliverable

Polished desktop workspace that boots cleanly on all three platforms and serves as the home for every engineering task.

---

## Phase 2 — Hardware Platform (P2)

**Goal:** Prometheus can communicate with virtually any engineering hardware.

### Tasks

1. **HAL expansion in Rust (`crates/hal-core`)**
   - Implement transport traits for each protocol family:
     - USB/USB-C/Thunderbolt/PCIe → `usbd` / `pciids` crates
     - UART/Serial/RS232/RS485 → `serialport` + custom framing
     - GPIO/SPI/I2C → platform-specific sysfs/libudev
     - CAN/LIN → `socketcan` + LIN stack
     - JTAG/SWD → OpenOCD libftdi/JLink bindings
     - HID/Bluetooth/BLE → `btleplug` / `hidapi`
     - WiFi/Ethernet → existing TCP/UDP stack
     - NFC/RFID → `nfc` crate + PN532 drivers
     - LoRa/Zigbee/Z-Wave → serial-attached radio modules
     - MQTT/Modbus/OPC-UA/BACnet → protocol-specific async clients

2. **Recovery workflows (Python layer)**
   - Android: ADB, Fastboot, EDL, Odin mode
   - Apple: DFU, Recovery mode
   - PC: BIOS, UEFI, TPM, Secure Boot manipulation
   - Embedded: JTAG/SWD flash, NAND/NOR/SPI EEPROM
   - Router/Drone/Vehicle: vendor-specific recovery protocols

3. **Hardware dashboard in desktop**
   - Real-time device tree view
   - Transport status indicators
   - Bus capture/log viewer

### Validation

- Protocol handshake success >= 98% on test devices
- Recovery workflow success >= 95%
- Mean device diagnosis time <= 3 min

---

## Phase 3 — Aether AI Runtime (P3)

**Goal:** Model-agnostic AI runtime that every Prometheus capability can use.

### Tasks

1. **Consolidated Rust runtime (`crates/aether-runtime`)**
   - Merge existing `ai-runtime` provider logic into `aether-runtime`.
   - Implement provider abstraction:
     - OpenAI, Anthropic, Gemini, OpenRouter (HTTP)
     - Ollama, LM Studio, llama.cpp, vLLM (OpenAI-compatible HTTP)
     - Custom provider trait for future integrations
   - Context engine:
     - Short-term memory (conversation window)
     - Long-term memory (vector store via Qdrant)
     - Project/user/engineering context injection
   - Routing layer:
     - Local-first policy
     - Cloud fallback with cost tracking
     - Automatic model selection by task type
     - Multi-model routing for parallel agents

2. **Python bridge (`aether/`)**
   - PyO3 bindings from Rust runtime to Python.
   - `aether/runtime.py` — high-level Python API used by agents and engineering modules.
   - Context persistence to SQLite/Qdrant.

3. **Agent runtime**
   - Planner, Researcher, Engineer, Tester, Documentation, Security, Recovery, Simulation, Verification, Memory agents.
   - Tool-calling framework wired to Prometheus capabilities (filesystem, terminal, git, hardware, SDK, plugins, knowledge graph, APIs).

### Deliverable

Users connect their preferred LLMs; Prometheus provides orchestration, context, tools, and memory.

---

## Phase 4 — Engineering Intelligence (P4)

**Goal:** Prometheus becomes an engineering partner, not just a tool collection.

### Tasks

1. **Repository analysis**
   - Git history mining, architecture graph extraction, dependency analysis.
   - Multi-language support (Rust, Python, TypeScript, C/C++).

2. **Design generation**
   - Proposal generation from natural language requirements.
   - Code scaffolding from design specs.

3. **Verification engine**
   - Automated test generation from requirements.
   - Property-based testing integration.

4. **Failure analysis**
   - Log/crash correlation.
   - Root-cause hypothesis generation.
   - Recovery plan synthesis.

5. **Engineering reports**
   - Automated architecture documentation.
   - Change-impact analysis.

### Deliverable

Verified engineering suggestions with confidence scoring and human-approval checkpoints.

---

## Phase 5 — Titan AI Platform (P5)

**Goal:** AI research and model development platform that powers Prometheus.

### Tasks

1. **Dataset pipeline**
   - Ingestion, cleaning, deduplication, tokenization.
   - Engineering-domain dataset curation tools.

2. **Training infrastructure**
   - Fine-tuning (SFT), preference (DPO), reinforcement (PPO/RFT).
   - Distributed training via `crates/tensor-engine`.
   - Experiment tracking and model registry.

3. **Optimization**
   - Quantization (GPTQ, AWQ, GGUF).
   - Compression and distillation.
   - ONNX/TensorRT/MLX export.

4. **Python SDK (`titan/`)**
   - Already exists. Expand coverage and align with Rust `crates/titan-core`.

### Deliverable

Prometheus can use Titan-trained or Titan-optimized models end-to-end.

---

## Phase 6 — High Performance Engine (P6)

**Goal:** Optimized inference for engineering workloads.

### Tasks

1. **Tensor engine (`crates/tensor-engine`)**
   - Expand beyond stub to actual tensor operations.
   - CPU SIMD (std::simd) and GPU (CUDA/WGPU) backends.

2. **Inference engine**
   - KV-cache management.
   - Continuous batching.
   - Attention kernel optimization (FlashAttention-style).

3. **Memory allocator**
   - Custom arena allocator for tensor buffers.
   - Memory-mapped model weights.

4. **Vector search**
   - HNSW index for knowledge retrieval.
   - Integration with Qdrant for distributed mode.

### Deliverable

Stable high-throughput inference profile on target GPUs.

---

## Phase 7 — Distributed Platform (P7)

**Goal:** Scale from one machine to engineering teams and clusters.

### Tasks

1. **Cluster control plane (Rust)**
   - Node discovery (mDNS + static config).
   - Work distribution and fault recovery.

2. **Distributed agents**
   - Remote agent spawning via SSH/WebSocket.
   - Cross-node capability routing.

3. **Distributed state**
   - CRDT-based knowledge graph sync.
   - Distributed simulation coordination.

4. **Distributed inference**
   - Model partitioning across nodes.
   - Tensor parallelism for large models.

### Deliverable

Multi-node execution with < 60s failure recovery and >= 75% cluster utilization.

---

## Phase 8 — Cloud Platform (P8)

**Goal:** Cloud collaboration without changing the desktop-first experience.

### Tasks

1. **Authentication and tenancy**
   - OIDC + passkey auth.
   - Organization and team hierarchy.

2. **Remote workspace sync**
   - Git-backed project sync.
   - Conflict-free workspace state merging.

3. **Remote hardware access**
   - Secure tunneling to team hardware.
   - Reservation and scheduling.

4. **API gateway and billing**
   - Rate-limited REST/GraphQL gateway.
   - Usage metering for cloud resources.

### Deliverable

Multi-tenant cloud platform with >= 99.9% API uptime and audited access controls.

---

## Phase 9 — SDK (P9)

**Goal:** Extensible ecosystem rather than a closed application.

### Tasks

1. **Plugin SDK (TypeScript + Rust)**
   - Stable plugin manifest format.
   - Capability declaration and permission model.
   - Hot-reload with state preservation.

2. **Driver SDK (Rust)**
   - HAL trait definitions.
   - Driver packaging and distribution.

3. **Extension SDK (Python)**
   - Engineering module interface.
   - Agent tool registration.

4. **Developer tooling**
   - `prometheus new <plugin|agent|driver>` scaffolding.
   - `prometheus pack` for distribution.
   - Package signing and verification.

### Deliverable

SDK with stable API versioning, compatibility matrix, and signed package publishing.

---

## Phase 10 — Engineering Applications (P10)

**Goal:** Specialized workspaces built on the platform.

### Studios

- Robotics Studio — kinematics, actuator control, simulation
- Firmware Studio — build, flash, debug, analyze
- Embedded Studio — MCU development, RTOS profiling
- Reverse Engineering Lab — disassembly, firmware analysis
- Security Lab — pentest tools, exploit analysis, hardening
- Networking Lab — packet capture, protocol analysis, SDN
- PCB Studio — schematic, layout, DRC, gerber generation
- CAD Integration — geometry import, digital twin generation
- AI Lab — model playground, prompt engineering, evaluation
- Vision Lab — CV pipelines, OCR, device inspection
- Audio Lab — signal analysis, FFT, audio processing
- Cloud Lab — remote device orchestration
- Vehicle Studio — ECU diagnostics, CAN/LIN analysis
- IoT Lab — sensor networks, edge deployment
- Industrial Automation Studio — PLC, SCADA, OPC-UA

### Deliverable

Cross-studio interoperability via shared contracts and consistent UX.

---

## Phase 11 — Platform 1.0 (P11)

**Final Product Checklist**

- [ ] Engineering Intelligence Platform (branding complete)
- [ ] Native desktop app (Tauri, Windows/Linux/macOS)
- [ ] Aether AI Runtime (providers, routing, context, agents)
- [ ] Titan AI Platform integration
- [ ] Hardware platform (20+ protocols, recovery workflows)
- [ ] Digital twin and knowledge platform
- [ ] Simulation and verification engine
- [ ] Plugin marketplace and SDK
- [ ] Enterprise collaboration (teams, remote hardware, billing)
- [ ] Autonomous engineering workflows with human-in-the-loop
- [ ] LTS, upgrade, backup, and disaster recovery workflows proven
- [ ] End-to-end workflow success >= 95%
- [ ] Customer-reported critical defects below release threshold

---

## Technology Stack (v3.0)

| Layer | Technology |
|-------|-----------|
| Desktop | Tauri 2 + React + TypeScript + xterm.js |
| Backend | Python (FastAPI) + Rust (performance-critical paths) |
| AI Runtime | Rust (`aether-runtime`) + PyO3 bridge |
| AI Research | Python + CUDA + `titan-core` |
| Databases | SQLite (local), PostgreSQL (cloud), Qdrant (vectors), DuckDB (analytics) |
| Hardware | Rust HAL core + Python recovery workflows |
| Distributed | Rust (actix/axum) + gRPC + MQTT |
| Security | TPM, Secure Boot, capability system, audit logging |

---

## Engineering Principles

1. **Platform First** — Build the platform before specialized applications.
2. **Local First** — Work offline whenever possible; cloud is optional.
3. **Provider Agnostic** — Users choose their AI models; Prometheus orchestrates them.
4. **Hardware Agnostic** — Support as many engineering devices and protocols as practical through modular drivers.
5. **Plugin Driven** — Extend functionality through SDKs rather than modifying the core.
6. **Workspace Centric** — Every capability accessible from both the graphical workspace and the integrated terminal.
7. **Engineering Before AI** — AI exists to enhance engineering workflows, not replace them.
