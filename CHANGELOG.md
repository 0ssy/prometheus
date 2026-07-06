# Changelog

All notable changes to Prometheus are documented in this file.

## [0.5.0-gamma] - 2026-07-06

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
