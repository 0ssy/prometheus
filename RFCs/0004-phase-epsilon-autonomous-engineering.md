# RFC 0004 — Phase Epsilon: Autonomous Engineering

**Status:** Draft

## Summary

Phase Epsilon gives Prometheus the ability to plan, suggest, and eventually
execute engineering workflows — from a raw idea all the way to deployment.
It is the "meta" phase: instead of just recovering devices, Prometheus
reasons about how to build and improve itself and the systems it manages.

## Goals

1. Capability Backlog — a living registry of AI limitations and how to address them.
2. Autonomous Engineering Engine — plan idea-to-deployment pipelines.
3. Improvement Suggester — scan the system for actionable enhancements.
4. Documentation scaffold — architecture, module specs, API standards,
   plugin SDK, coding standards, threat model, security model.

## Non-goals

- Actually writing code or deploying binaries (v0.1 is planning only).
- Building hardware or performing physical experiments.
- ML-based code generation or architecture design.

## Design

- The Autonomous Engineering Engine produces structured plans recorded as
  knowledge-graph facts.
- The Capability Backlog is a simple in-memory list for v0.1, persisted
  to the knowledge graph in future versions.
- Improvement suggestions are rule-based, not ML, per the project's
  explicit non-goal for v0.1.

## Pipeline

```
Idea → Architecture → Code → Simulation → Testing → Deployment
```

Each stage is a `PipelineStep` dataclass with title, description, estimated
effort, and dependencies. Plans are immutable once created.

## Open Questions

- Should the pipeline support branching (parallel stages)?
  Answer: v0.1 is linear only. Parallel stages are a future addition.
- Should plans be executable (actually run tests, write files)?
  Answer: v0.1 is read-only planning. Execution is a major version bump.
- Should the capability backlog be user-editable via API?
  Answer: v0.1 is code-defined. User-facing backlog editor is future work.
