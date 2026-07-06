# ADR 0005: Enforce declared ownership gating for engineering actions

- Status: Accepted
- Date: 2026-07-06
- Deciders: Prometheus maintainers
- RFC Links: RFC 0000, RFC 0002

## Context

Engineering endpoints and workflows touch high-risk targets
(firmware images, disk/partition artifacts). A bypassable query flag was
insufficient as an ownership control mechanism.

## Decision

Use `core/ownership_registry.py` as the persistent declared-ownership gate.
Actions in engineering and autonomous flows must check declaration before
processing.

## Rationale

This makes ownership intent explicit and persistent while avoiding false
claims of cryptographic verification not yet implemented.

## Consequences

- Pros: stronger safety posture, clearer audit trail.
- Cons: still a declaration model (not attestation/verification).

## Alternatives considered

- Request-level ownership flags.
- Immediate shift to full device attestation before gating anything.
