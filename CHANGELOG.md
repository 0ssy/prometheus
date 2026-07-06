# Changelog

All notable changes to Prometheus are documented in this file.

## [0.4.0-delta] - 2026-07-06

Codename: **Daedalus**  
Status: **IN_PROGRESS**

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
