# System Architecture

This describes the whole system's shape. Individual design decisions
live in `RFCs/` — this document is the map, not the reasoning behind
each landmark on it.

## Layer diagram

```
Applications           (none built yet — API consumers, future frontend)
──────────────
AI Agents              agents/, autonomous/  (EchoAgent, EngineeringAgent)
──────────────
Prometheus Core        core/bootstrap.py — the single boot sequence
──────────────
Knowledge Engine        reasoning/  (knowledge graph — subject/predicate/object facts)
Verification Engine     engineering/boot_chain.py, crypto_verify.py
Memory Engine           memory/  (long-term memory store)
──────────────
Plugin System           plugins/
──────────────
Hardware Abstraction    devices/  (Device contract, Registry, Simulated/Serial)
──────────────
Physical World          real hardware — currently: real GPT disks tested,
ESP32 pending
```

## Boot sequence

See `core/bootstrap.py` directly — it's short and deliberately
readable as the single source of truth for "what happens when
Prometheus starts," rather than this document trying to describe it
in prose and drifting out of sync with the code.

## Phase-to-layer mapping

| Phase | Lives in | Layer |
|---|---|---|
| Alpha | `core/`, `agents/`, `plugins/`, `memory/`, `reasoning/` | Core + Knowledge + Memory |
| Beta | `devices/` | Hardware Abstraction |
| Gamma | `engineering/` | Verification Engine |
| Delta | `digital_twin/` | Aggregates Knowledge Engine facts |
| Epsilon | `autonomous/` | AI Agents (one specific agent) |

## Cross-cutting: ownership

`core/ownership_registry.py` isn't a layer — it's a gate every
`engineering/` module and Epsilon's agent check before acting. See
`architecture/security.md` and RFC 0000.

## Full detail

- `docs/ARCHITECTURE.md` — narrative version with the "what limits
  exist right now" framing
- `RFCs/0000` through `0004` — the actual design decisions, including
  what was rejected and why
