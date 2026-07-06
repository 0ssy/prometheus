# ADR 0002: Split unstructured memory from structured knowledge facts

- Status: Accepted
- Date: 2026-07-06
- Deciders: Prometheus maintainers
- RFC Links: RFC 0003

## Context

Prometheus tracks both free-form operational notes and strongly-typed
state/event facts used by higher layers (digital twin, autonomous agent
evaluation).

## Decision

Retain two paths:

- `memory/` for unstructured long-term entries.
- `reasoning/` for structured append-only facts.

## Rationale

This avoids overloading one storage pattern with conflicting semantics.
Twin/history derivation relies on append-only facts, while memory notes
need flexible content and tags.

## Consequences

- Pros: clear boundaries and cleaner query patterns.
- Cons: contributors must choose the right path per data type.

## Alternatives considered

- Single unified table/store for both notes and facts.
