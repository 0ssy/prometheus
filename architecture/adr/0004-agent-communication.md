# ADR 0004: Route agents through centralized manager dispatch

- Status: Accepted
- Date: 2026-07-06
- Deciders: Prometheus maintainers
- RFC Links: RFC 0004

## Context

As agents grow in number and complexity, direct module-to-module calling
creates brittle coupling and inconsistent logging/observability.

## Decision

All runtime agent execution goes through `agent_manager.dispatch(...)` and
the API dispatch endpoint.

## Rationale

A single dispatch path provides one place for registration, execution
control, and future policy hooks (authorization, tracing, rate limits).

## Consequences

- Pros: consistency, observability, easier governance.
- Cons: agents must fit manager contract and context shape.

## Alternatives considered

- Direct invocation of agent classes from routes/services.
