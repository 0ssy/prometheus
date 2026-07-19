# Capability-First Platform Roadmap

## Goal
Shift Prometheus from an "app launcher" to a **capability platform**. Every new feature must answer: "What new capability does the platform gain?" If the answer is "none," don't build it.

## Current State
A `CapabilityManager` already exists (`core/capabilities.py`) with `register`, `discover`, `execute`, `authorize`, `history`. Hardware capabilities are registered via `services/capability_registry.py` and exposed through `/capabilities/execute`. The infrastructure is sound — it just needs to become the primary organizing principle instead of the UI apps.

## Core Principle
**Build once, use everywhere.** A capability becomes usable by Assistant, Terminal, SDK, Plugins, Automation, and future apps simultaneously.

```
Platform
  └── Capability Layer (register, discover, authorize, execute, sync)
        ├── USB Stack
        ├── Bluetooth Stack
        ├── Recovery Framework
        ├── Firmware Parsing
        ├── AI Runtime
        ├── Knowledge Graph
        ├── Security Model
        └── ...
              ├── Assistant (consumes via natural language)
              ├── Terminal (consumes via CLI grammar)
              ├── SDK (consumes via typed API)
              ├── Plugins (consume via marketplace)
              └── Automation (consumes via triggers + actions)
```

---

## Capability Taxonomy

### Layer 1: Platform Core (already exists, keep stable)
- Kernel
- Event Bus
- HAL / Driver Framework
- Scheduler
- Storage (SQLite + filesystem)
- Permission System
- Plugin Runtime
- Capability Registry (`CapabilityManager`)

### Layer 2: Infrastructure Capabilities
| Capability | Current State | Implementation Lang | Notes |
|------------|--------------|---------------------|-------|
| Filesystem | Exists (`files/`) | Python | Extend with watch/notify |
| Networking | Partial | Rust (tokio) | TCP/UDP/HTTP/MQTT/CoAP |
| USB | Partial (HAL drivers) | Rust (nusb) | Enumerate, claim, transfer |
| Bluetooth / BLE | Partial (HAL) | Rust (btle) | GATT, advertising, scanning |
| WiFi | Partial | Rust | Station + AP mode |
| Ethernet | Partial | Rust/C | PHY detection, link state |
| CAN / LIN | Partial (HAL) | Rust (socketcan) | Frame send/receive |
| SPI / I²C / UART / GPIO | Partial (HAL) | Rust/C | Bit-banged + kernel drivers |
| PCIe / JTAG / SWD | Partial (HAL) | Rust/C | Low-level bus access |

### Layer 3: Engineering Capabilities
| Capability | Current State | Implementation Lang | Notes |
|------------|--------------|---------------------|-------|
| Recovery Framework | Partial (`epsilon/`) | Python + Zig | ADB, Fastboot, EDL, DFU, BIOS |
| Firmware Parsing | Partial (`firmware/`) | Python + Rust | ELF, bin, hex, uf2, dfu |
| Binary Analysis | Stub | Rust (goblin) | Disasm, symbols, sections |
| Digital Twin | Partial (`simulation/`) | Python | State sync, failure injection |
| Simulation Engine | Partial (`simulation/`) | Python + Rust | Monte Carlo, fault trees |
| Protocol Decoder | Stub | Rust | UART, SPI, CAN, BLE sniff + decode |
| Oscilloscope Capture | Stub | Python + C (libusb) | Rigol, Sigltek, Hantek |
| Logic Analyzer | Stub | Rust + C (libsigrok) | Saleae, DSLogic |
| PCB Inspection | Stub | Python + OpenCV | AOI, solder joint, silkscreen |

### Layer 4: AI Capabilities
| Capability | Current State | Implementation Lang | Notes |
|------------|--------------|---------------------|-------|
| LLM Chat | Partial (`assistant/`) | Python + Rust | OpenAI-compatible, streaming |
| Embeddings | Stub | Python + Rust | Local + remote providers |
| Memory | Partial (`memory/`) | Python | Short-term + long-term |
| Tool Calling | Partial (`assistant/`) | Python | Function calling, approval flow |
| Planning | Partial (`agents/`) | Python | Task graph, delegation |
| Multi-Agent | Partial (`agents/`) | Python | Consensus, coordination |
| Vision | Stub | Python + Rust (ort) | OCR, object detection |
| Speech | Stub | Python | STT, TTS |
| Code Generation | Stub | Python | LSP-aware, sandboxed |

### Layer 5: Security Capabilities
| Capability | Current State | Implementation Lang | Notes |
|------------|--------------|---------------------|-------|
| Permission Engine | Exists (`security/`) | Python | RBAC, capability tokens |
| Audit Logging | Exists (`security/`) | Python | Immutable append-only |
| Sandboxing | Stub | Rust | Process + plugin isolation |
| Driver Signing | Stub | Rust + C | Authenticode, PKCS#7 |
| Secure Boot | Stub | Rust + Zig | UEFI, measured boot |
| TPM | Partial (HAL) | Rust (tss-esapi) | PCR, keys, attestation |
| Encryption | Partial | Rust (rust-crypto) | AES-GCM, RSA, ECC |

### Layer 6: Cloud Capabilities
| Capability | Current State | Implementation Lang | Notes |
|------------|--------------|---------------------|-------|
| Authentication | Partial (`enterprise/`) | Python + Rust | OAuth2, OIDC, mTLS |
| Sync | Partial (`distributed/`) | Rust | CRDT-based, eventually consistent |
| Remote Devices | Stub | Rust + Python | Tunnel, proxy, relay |
| Remote Agents | Stub | Rust | Distributed task execution |
| Marketplace | Partial (`marketplace/`) | Python | Plugin + capability registry |
| Organizations | Partial (`enterprise/`) | Python | Org, project, team, user |
| Team Workspaces | Stub | Python | Shared state, RBAC |

---

## Capability Interface Contract

Every capability MUST implement:

```python
class Capability(Protocol):
    name: str          # e.g. "hardware.usb.enumerate"
    target: str        # e.g. "hardware"
    version: str       # semver
    permissions: set[str]
    register(manager: CapabilityManager) -> None
    execute(payload: dict[str, Any], context: ExecutionContext) -> Result
    health() -> HealthStatus
```

And be discoverable via:
- `GET /capabilities` — list all registered capabilities
- `POST /capabilities/{name}/execute` — execute with authz
- `GET /capabilities/{name}/health` — liveness check
- SDK: `sdk.capabilities.discover()`, `sdk.capabilities.execute()`
- Terminal: `capability list`, `capability run <name>`
- Assistant: natural language → capability routing via Aether

---

## Consumer Exposure

A capability is not useful until it is reachable from every consumer surface:

| Consumer | Mechanism | Example |
|----------|-----------|---------|
| **Assistant** | Aether tool dispatch | "List USB devices" → `hardware.usb.enumerate` |
| **Terminal** | Command grammar | `usb list` → `hardware.usb.enumerate` |
| **SDK** | Typed method | `sdk.hardware.usb.enumerate()` |
| **Plugins** | Marketplace registry | Plugin declares `requires: [hardware.usb]` |
| **Automation** | Trigger → Action | `on usb.connect → firmware.dump` |
| **Frontend Apps** | API client | `api.executeCapability("hardware.usb.enumerate", {})` |

---

## Implementation Rules

1. **No new UI apps.** Every new feature is a capability first, UI second.
2. **Capabilities are language-agnostic.** The registry is Python, but executors can be:
   - Python (rapid iteration, orchestration)
   - Rust (performance, safety, systems programming)
   - Zig (embedded, bare metal)
   - C/C++ (existing drivers, vendor SDKs)
   - Go (networking, cloud services)
3. **Capabilities are composable.** `hardware.recovery` can call `firmware.parse` internally.
4. **Capabilities are observable.** Every execution emits `CapabilityExecutedEvent` and is recorded in history.
5. **Capabilities are permissioned.** Every capability declares its permission set at registration time.
6. **Capabilities are syncable.** `CapabilitySynchronizer` replicates capability metadata across distributed nodes.

---

## Rollout Order

### RC4 — Capability Foundation
- [ ] Audit all existing subsystems and map them to capabilities (this document)
- [ ] Refactor `CapabilityManager` into a proper capability registry with namespacing (`<domain>.<action>`)
- [ ] Add capability versioning and dependency declarations
- [ ] Ensure every existing backend endpoint delegates to a registered capability
- [ ] Expose `/capabilities` discovery endpoint
- [ ] Add `sdk.capabilities` namespace to frontend SDK

### RC5 — Hardware Capabilities
- [ ] USB enumeration + transfer (Rust, nusb)
- [ ] Bluetooth / BLE scan + GATT (Rust)
- [ ] CAN bus frame I/O (Rust + socketcan)
- [ ] UART / SPI / I²C bit-level (Rust/C)
- [ ] GPIO / PWM (Rust + sysfs/libgpiod)
- [ ] NFC / RFID (Rust, PN532)
- [ ] LoRa / Zigbee / Z-Wave (Rust)

### RC6 — Recovery + Firmware
- [ ] Unified Recovery Framework (Python + Zig for bootloader interaction)
- [ ] Firmware format parsers (ELF, bin, hex, uf2, dfu) — Rust
- [ ] Android: ADB, Fastboot, EDL, Odin providers
- [ ] Embedded: DFU, J-Link, SWD recovery
- [ ] Desktop: BIOS/UEFI recovery, TPM reset

### RC7 — Engineering Capabilities
- [ ] Protocol decoder framework (Rust)
- [ ] Binary analysis (Rust, goblin)
- [ ] Oscilloscope + Logic Analyzer capture (Python + C)
- [ ] PCB inspection (Python + OpenCV)

### RC8 — AI Runtime Expansion
- [ ] Embeddings capability (local + remote)
- [ ] Memory consolidation (short-term → long-term)
- [ ] Vision capability (OCR, object detection)
- [ ] Speech capability (STT, TTS)

### RC9 — Security Hardening
- [ ] Sandboxed plugin execution (Rust)
- [ ] Driver signing verification
- [ ] Secure boot chain validation
- [ ] TPM-backed key storage

### RC10 — Cloud + Distribution
- [ ] Remote device tunnel (Rust + WebTransport)
- [ ] Distributed capability execution
- [ ] Team workspace sync
- [ ] Marketplace capability packaging

---

## Success Criteria

- [ ] Every platform feature is a registered `Capability`
- [ ] Every capability is reachable from Assistant, Terminal, SDK, Plugins, Automation
- [ ] No capability logic lives only inside a single UI app
- [ ] Capabilities can be implemented in any supported language
- [ ] 355+ tests continue to pass through all capability refactors
- [ ] Zero new UI apps added until core capabilities are excellent

---

## Out of Scope

- Rust PTY replacement for browser terminal (RC2 item, separate)
- UI redesign of existing apps
- New frontend features that do not expose a new capability
- Any capability that cannot be registered, discovered, authorized, and executed
