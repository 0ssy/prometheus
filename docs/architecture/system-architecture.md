# System Architecture

## Overview

Prometheus is a local-first, offline-capable device intelligence platform.
It combines firmware inspection, partition mapping, boot-chain verification,
digital-twin state tracking, and autonomous engineering planning into a
single coherent system.

## Core Principles

1. **Local-first** — all intelligence runs on the host machine. Cloud is
   an optional plugin, not a dependency.
2. **Offline-capable** — no network required for core functionality.
3. **Honest about limits** — declared ownership, not verified; simulated
   hardware, not mocked outcomes; rules-based health, not ML guesses.
4. **Auditable** — every action writes a fact to the knowledge graph.
5. **Extensible** — plugins, agents, and new modules hook into the same
   registry and event system.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend / CLI Layer                     │
│  (React / Electron / Tauri / Mobile companion)               │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP / WebSocket
┌───────────────────────────▼─────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Alpha     │  │    Beta     │  │       Gamma         │  │
│  │  Plugins    │  │   Devices   │  │  Firmware / Boot    │  │
│  │  Agents     │  │  Registry   │  │  Chain / Recovery   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Delta     │  │  Epsilon    │  │       Core          │  │
│  │  Digital    │  │ Autonomous  │  │  Config / Logger    │  │
│  │  Twin       │  │ Engineering │  │  DB / Scheduler     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    Knowledge Graph                           │
│                  (SQLite / PostgreSQL)                        │
│  Facts: subject, predicate, object, created_at               │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    Hardware Layer                            │
│  Serial / USB / Wi-Fi / GPIO / Bluetooth                      │
│  Simulated devices for testing                                │
└─────────────────────────────────────────────────────────────┘
```

## Module Map

| Phase | Module | Responsibility |
|-------|--------|----------------|
| Alpha | Plugin Manager | Load, run, and lifecycle plugins |
| Alpha | Agent Manager | Dispatch agents with context |
| Alpha | Memory Store | Remember and recall tagged entries |
| Alpha | Reasoning Graph | Assert and query knowledge-graph facts |
| Beta | Device Registry | Track connected devices by transport |
| Beta | Simulated Device | Fake hardware for testing agents |
| Beta | Serial Device | Real serial-port communication |
| Gamma | Partition Mapper | Read GPT/MBR partition tables |
| Gamma | Firmware Inspector | Fingerprint firmware images |
| Gamma | Boot Chain Analyzer | Verify Ed25519 signatures |
| Gamma | Recovery Planner | Produce official recovery steps |
| Gamma | Device Simulator | Firmware-bearing sim with real crypto |
| Delta | Digital Twin Engine | Materialized view over knowledge graph |
| Epsilon | Autonomous Engineering | Idea-to-deployment pipeline planner |
| Core | Config | Centralized configuration |
| Core | Logger | Structured logging |
| Core | Database | SQLAlchemy session management |
| Core | Scheduler | Background job runner |
| Core | Ownership Registry | Persistent declared-ownership store |

## Data Flow

1. **Ingest** — devices connect, events are asserted as facts.
2. **Inspect** — Gamma modules read firmware/partitions/boot chains,
   each requiring persistent ownership declaration.
3. **Twin** — Delta aggregates facts into a nine-field digital twin.
4. **Plan** — Epsilon produces engineering plans and improvement suggestions.
5. **Act** — Beta modules can write to devices; Gamma and Delta are read-only.

Every stage writes to the knowledge graph, so the full history is queryable
at any time.
