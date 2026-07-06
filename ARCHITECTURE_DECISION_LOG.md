# Architecture Decision Log

## 2026-07-06 — Delta/Epsilon/Omega Roadmap Lock-In

### Context
With Gamma frozen, the project needed a stable forward roadmap for the next three phases to
avoid ad-hoc milestone drift.

### Decision
1. Keep the phase sequence: Delta (Daedalus), Epsilon (Hephaestus), Omega (Olympus).
2. Define clear objectives and measurable Definitions of Done per phase.
3. Require roadmap changes to be made through RFC updates.
4. Start implementation scaffolding for Delta/Epsilon/Omega services and APIs.

### Consequences
- Phase scope is explicit and reviewable.
- New work aligns to measurable outcomes instead of feature drift.
- Platform now has executable upgrade paths for simulation lab, hardware abstraction, and ecosystem layers.

## 2026-07-06 — Phase Gamma Freeze Checkpoint (Helios)

### Context
Gamma introduced the dedicated knowledge layer and independent knowledge engine API surface.
The milestone reached a stable boundary for graph, ontology, provenance, query, and learning.

### Decision
1. Freeze Gamma as `v0.3.0-gamma`.
2. Mark codename `Helios` with status `COMPLETE`.
3. Route future enhancements to the next phase instead of expanding Gamma scope.

### Consequences
- `v0.3.0-gamma` is the canonical checkpoint for knowledge-layer foundations.
- Gamma remains feature-frozen except for bug fixes.

## 2026-07-06 — Phase Gamma (Helios) Knowledge Layer

### Context
Beta established capability execution and simulation-first workflows. The next step required
a durable knowledge layer that can answer what Prometheus knows, how certain it is, and where
that knowledge came from.

### Decision
1. Added `knowledge/` package with graph, node, edge, query, ontology, provenance, and learning modules.
2. Introduced `KnowledgeEngine` as the only knowledge access boundary for services.
3. Added immutable knowledge edges with confidence and provenance metadata.
4. Added query endpoints for recovery support, simulation failures, unused capabilities, and learning history.
5. Updated design principles to explicitly enforce immutable knowledge with evolving understanding.

### Consequences
- Knowledge is append-only and auditable.
- Query use cases no longer require raw SQL at API boundaries.
- Learning outcomes from simulation workflows are now persisted and reusable.

## 2026-07-06 — Phase Beta (Atlas) Intelligence Layer

### Context
After freezing Alpha (Genesis), the next objective was to prove Prometheus can reason
about simulated systems before direct execution.

### Decision
1. Added a capability framework (`CapabilityManager`) with register/discover/authorize/execute/history.
2. Introduced a Prometheus Core Kernel (`kernel/runtime.py`) owning lifecycle, permissions, and runtime status.
3. Added simulation and reasoning pipeline modules (`simulation/engine.py`, `reasoning/pipeline.py`).
4. Added a digital-device service projection (`services/digital_device_service.py`) for state/events/memory.
5. Added observability store for metrics, traces, and event history (`core/observability.py`).
6. Exposed Beta workflow endpoint: `/beta/workflow/{device_id}`.

### Consequences
- Capability execution is now first-class and auditable.
- Core runtime can report health/status independently of frontend.
- Workflows now prefer simulation and recommendation before execution.

## 2026-07-06 — Phase Alpha Freeze Checkpoint (Genesis)

### Context
Phase Alpha reached a stable architectural baseline with contract-first interfaces,
container-based wiring, event-driven internals, and an end-to-end happy path.
Further changes in the same phase would blur milestone boundaries.

### Decision
1. Freeze Phase Alpha as a completed checkpoint.
2. Create git tag `v0.1.0-alpha`.
3. Assign codename `Genesis` and status `COMPLETE`.
4. Treat all new architectural work as post-Alpha milestones.

### Rationale
- Milestone integrity: stable checkpoints make architectural evolution auditable.
- Traceability: an immutable tag anchors future comparisons and reviews.
- Engineering discipline: phase transitions should be explicit, not implicit.

### Consequences
- `v0.1.0-alpha` becomes the canonical reference for the Alpha baseline.
- New work should avoid retroactively redefining Alpha scope.
- Future release notes can compare against this tag as the first stable architecture checkpoint.

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
