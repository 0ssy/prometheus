# Architecture Decision Log

## 2026-07-06 — Contract-First Architecture & Dependency Injection

### Context
After three iterations (Alpha through Epsilon), Prometheus had working modules but no canonical place for interfaces. Subsystems imported concrete classes directly, making testing difficult and coupling high. Memory and reasoning were function-based services in a sea of classes, and the startup sequence had no single source of truth for wiring.

### Decision
1. Centralized all subsystem interfaces in `api/` as abstract base classes (`PluginApi`, `AgentApi`, `DeviceApi`, `MemoryApi`, `ReasoningApi`).
2. Introduced `ServiceContainer` for lightweight dependency injection.
3. Refactored `MemoryStore` and `ReasoningStore` from functions to classes implementing `MemoryApi` and `ReasoningApi`.
4. Retained old module-level function signatures as backward-compatible wrappers.
5. Updated `core/bootstrap.py` to return the container and wire subsystems explicitly.
6. Added the first automated tests (36 passing) for managers, stores, and the bootstrap sequence.

### Rationale
- **Contracts over folders**: The codebase already had base.py contracts scattered across modules. Centralizing them in `api/` makes the platform surface explicit and discoverable.
- **DI over singletons**: Singletons were already used for managers, but wiring was implicit. The container makes dependencies explicit and testable.
- **Functions to classes**: `memory.store` and `reasoning.graph` were the only function-based services. Converting them to classes made all subsystems consistent and mockable.
- **Backward compatibility**: Keeping old function signatures as thin wrappers avoided a big-bang migration and kept the API layer working without changes beyond the container refactor.
- **Tests protect architecture**: With dozens of planned implementations, tests became essential before more refactoring.

### Consequences
- Every new subsystem must expose an interface in `api/`.
- New code should access services via `container.get("service_name")` rather than importing singletons directly.
- The old singleton pattern (`plugin_manager`, `agent_manager`, `device_registry`, `memory_store`, `reasoning_store`) is preserved for backward compatibility with existing API endpoints.
- `backend/main.py` was updated to use the container for all service lookups.

### Lessons Learned
- Start with interfaces early. Adding `api/` after several modules existed required touching many files, but the change was mechanical and low-risk because the contracts already existed in scattered `base.py` files.
- A lightweight container is better than a framework. `ServiceContainer` is roughly 20 lines of code and gives 90% of the value of complex DI libraries.
- Backwards compatibility matters. Keeping old function signatures as thin wrappers avoided a big-bang migration and kept the API layer working.
- Tests make refactoring safe. Adding 36 unit tests before the bootstrap change made it possible to verify every subsystem still works after wiring.
- The happy path is a powerful milestone. Having a script that exercises every subsystem end-to-end proves the architecture holds together.

## 2026-07-05 — Phase Epsilon Autonomous Engineering

### Context
Phase Delta proved the platform could materialize a device twin from the knowledge graph. The next capability milestone was autonomous proposal generation.

### Decision
Built `EngineeringAgent` executing the propose -> simulate -> test -> report pipeline. Hard-coded a non-deployment stop in the agent contract.

### Rationale
- Reuse existing agent/plugin dispatch paths — no new API surface needed.
- Keep simulation and testing pure functions for testability.
- Append-only knowledge graph records every proposal outcome.

## 2026-07-05 — Phase Delta Digital Twin Engine

### Context
Phase Gamma produced firmware and partition artifacts. The platform needed a way to aggregate them into a coherent device view.

### Decision
Built `DeviceTwin` as a materialized view over the knowledge graph, never a second source of truth. Read-only by construction.

### Rationale
- Append-only knowledge graph provides natural history.
- Simple rules-based health scoring for v0.1 (no ML per RFC 0003's explicit non-goal).
- Live device state blended with historical facts.

## 2026-07-04 — Phase Beta Device Interface (RFC 0001)

### Context
The platform needed to interact with physical devices without binding every downstream caller to transport-specific libraries.

### Decision
Defined `Device` ABC with `connect`, `disconnect`, `read`, `write`, `status`, plus defaults for `diagnose`, `verify`, `recover`. Built `DeviceRegistry` as the canonical lookup.

### Rationale
- Honor-system `ownership_declared` flag (not verified) for v0.1.
- Simulated transport for testing, serial transport for real hardware.
- Registry is in-memory only (devices reconnect after restart).
