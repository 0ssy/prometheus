# Decision Records

## DEC-001 — Local-First Architecture

**Decision**: Prometheus runs entirely on the host machine. Cloud is an optional plugin.

**Rationale**: Offline capability, privacy, and no dependency on external services.

**Consequences**: All core modules must work without network. Cloud sync is deferred.

## DEC-002 — Declared Ownership, Not Verified

**Decision**: v0.1 uses an honor-system `ownership_declared` flag, persisted out-of-band.

**Rationale**: Cryptographic ownership verification (TPM, manufacturer certificates) is
significant engineering work. The declared model closes the URL-bypass gap while
keeping v0.1 achievable.

**Consequences**: Gamma modules trust the persistent registry. Future versions may
upgrade to verified ownership.

## DEC-003 — Ed25519 for Cryptographic Verification

**Decision**: Use Ed25519 via the `cryptography` library for signature verification.

**Rationale**: Ed25519 is fast, widely supported, and has a clean API. No complex
certificate chains or parameter selection needed.

**Consequences**: Prometheus verifies signatures but never signs. Key management is
the caller's responsibility.

## DEC-004 — Append-Only Knowledge Graph

**Decision**: Facts are never updated or deleted. `assert_fact()` is write-only.

**Rationale**: Simplicity, auditability, and natural history. Updating facts requires
complex merge logic and breaks the append-only mental model.

**Consequences**: The digital twin is a materialized view over immutable facts.
History is free.

## DEC-005 — Rules-Based Health, Not ML

**Decision**: v0.1 health scoring is a simple weighted rules engine.

**Rationale**: ML requires training data, validation, and ongoing maintenance.
Rules are deterministic, explainable, and sufficient for v0.1.

**Consequences**: Health scores may be crude. ML is a Delta or Epsilon addition.

## DEC-006 — Python for Orchestration, Rust Future

**Decision**: Python for AI orchestration and API. Rust planned for performance-critical
embedded components.

**Rationale**: Python has the best AI/ML ecosystem and fastest development velocity.
Rust is better for bare-metal firmware and safety-critical code.

**Consequences**: The core is Python today. Embedded tooling may migrate to Rust.
