# RFC 0002 — Phase Gamma: Engineering Core

**Status:** Implemented v0.1 (2026-07-05) — Firmware Inspector, Boot Chain Analyzer, Recovery Planner, Device Simulator, Partition Mapper all live and verified against real hardware (real GPT disk) and real Ed25519 signatures.

## Summary

Phase Gamma gives Prometheus the ability to inspect, verify, and recover
physical devices — firmware images, partition tables, and boot chains.
It is the boundary between "the thing exists" (Beta) and "the thing is
healthy and recoverable" (Delta).

## Goals

1. Firmware Inspector — fingerprint a dumped firmware image, report
   size, SHA-256, and ESP32 header when present.
2. Partition Mapper — read a raw disk path or image, parse GPT (best-
   effort), report MBR or unknown honestly.
3. Boot Chain Analyzer — verify an Ed25519 signature over firmware
   bytes; report valid / invalid / unknown.
4. Recovery Planner — given inspection results, produce an ordered list
   of official recovery options. Never executes anything.
5. Device Simulator — a firmware-bearing simulated device with a real
   Ed25519 keypair so Boot Chain can be tested without hardware.

## Non-goals

- Writing to disks or flashing firmware (explicitly out of scope).
- ML-based health scoring (deferred to Delta).
- Cryptographic ownership verification (deferred — v0.1 uses declared
  ownership only, see RFC 0000).

## Design

- Every Gamma module is READ-ONLY. There is no write path in any of
  these modules.
- Every Gamma module requires ownership_declared=True before it will
  touch a target. This is enforced at the function level, not left to
  callers to remember.
- Cryptographic verification uses Ed25519 via the `cryptography`
  library. Verification only — Prometheus never signs on a device's
  behalf.
- The Device Simulator generates a fresh Ed25519 keypair per instance
  and signs its own firmware bytes, so tampering tests use real
  signature verification, not mocked True/False.

## Ownership

The ownership-verification gap this RFC depends on (RFC 0000) has been
upgraded from a per-request boolean flag to a persistent, out-of-band
declaration — see core/ownership_registry.py. Still an honor system,
but no longer bypassable by just typing a query parameter.

## Open questions

- Should the Boot Chain Analyzer support RSA/ECDSA in addition to
  Ed25519? Answer: v0.1 is Ed25519 only. Add others when a real device
  needs it.
- Should Recovery Planner produce machine-readable JSON-LD plans?
  Answer: v0.1 produces plain JSON. JSON-LD is a Delta or Epsilon
  addition.
- Should Firmware Inspector parse ARM/RISC-V ELFs or only ESP32 .bin
  images? Answer: ESP32-shaped images only for v0.1. Generic ELF
  parsing is a separate module.
