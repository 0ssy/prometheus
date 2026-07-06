# ADR 0001: Keep explicit plugin loading at startup

- Status: Accepted
- Date: 2026-07-06
- Deciders: Prometheus maintainers
- RFC Links: RFC 0001

## Context

Prometheus needs predictable startup behavior and safe extension points.
Dynamic plugin discovery from arbitrary paths introduces security and
operational risks before a full trust and signing model exists.

## Decision

Plugin loading remains explicit and code-driven in the bootstrap path
via `plugin_manager.register(...)`.

## Rationale

Explicit registration is auditable, deterministic, and secure-by-default.
It also keeps startup behavior easy to reason about while extension
contracts are still stabilizing.

## Consequences

- Pros: deterministic startup, low surprise, easier security posture.
- Cons: adding a plugin requires code change and release.

## Alternatives considered

- Dynamic filesystem/plugin package discovery at runtime.
- Remote plugin registries.
