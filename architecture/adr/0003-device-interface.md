# ADR 0003: Preserve one transport-agnostic Device contract

- Status: Accepted
- Date: 2026-07-06
- Deciders: Prometheus maintainers
- RFC Links: RFC 0001

## Context

Prometheus must support simulated and real devices without forcing agents
and plugins to depend on transport-specific libraries.

## Decision

Maintain `devices/base.py` as the single transport-agnostic contract used
through the registry by higher layers.

Optional capability methods (`diagnose`, `verify`, `recover`) are concrete
defaults returning unsupported, not abstract requirements for all devices.

## Rationale

A single contract decouples consumers from hardware details and allows
incremental transport adoption. Concrete defaults avoid breaking existing
subclasses while still expressing long-term capability direction honestly.

## Consequences

- Pros: stable integration surface and low coupling.
- Cons: optional capabilities may be partially implemented per transport.

## Alternatives considered

- Separate interface per transport.
- Making all advanced capability methods abstract immediately.
