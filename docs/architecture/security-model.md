# Security Model

## Ownership Model

v0.1 uses **declared ownership**, not verified ownership.

- `ownership_declared=True` is an honor-system flag.
- Declarations are persisted to `config/owned_devices.json`.
- Gamma modules check the persistent registry, not a per-request flag.
- No cryptographic proof of ownership is required or performed.

Future versions may add:
- Option 2: TPM-backed device identity attestation.
- Option 3: Manufacturer-signed ownership certificates.

## Cryptographic Verification

- **Algorithms**: Ed25519 for signatures, SHA-256 for hashing.
- **Library**: `cryptography` (Python).
- **Scope**: Verification only. Prometheus never signs on a device's behalf.
- **Key management**: Public keys are supplied by the caller or simulator.
  Private keys are never stored by Prometheus.

## Data Integrity

- Knowledge graph facts are append-only.
- No update or delete operations on facts.
- `created_at` timestamps are set by the database, not the client.

## Transport Security

- Local API runs on `127.0.0.1:8000` by default.
- No TLS in v0.1 (local-only threat model).
- Cloud sync (future) must use TLS with certificate pinning.

## Secrets Management

- No API keys, tokens, or passwords in the codebase.
- If cloud plugins require credentials, they must be provided via
  environment variables or a secrets manager, never hardcoded.
