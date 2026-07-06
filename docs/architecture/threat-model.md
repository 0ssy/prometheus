# Threat Model

## Assets

1. **Firmware images** — intellectual property, may contain proprietary code.
2. **Partition tables** — may reveal sensitive data layout.
3. **Boot chain signatures** — cryptographic proof of firmware integrity.
4. **Device telemetry** — operational data from connected hardware.
5. **Knowledge graph** — historical record of all actions and facts.
6. **Ownership declarations** — authorization to act on a target.

## Threats

| Threat | Likelihood | Impact | Mitigation |
|--------|-----------|--------|------------|
| Unauthorized firmware read | Medium | High | Persistent ownership declarations; no bypassable flags |
| Firmware tampering | Medium | Critical | Ed25519 signature verification; recovery planner halts on invalid |
| Partition table corruption | Low | Medium | Read-only access; no write path in Gamma |
| Knowledge graph poisoning | Low | Medium | Append-only facts; no update/delete |
| Physical device theft | Medium | High | Ownership declarations are per-device, not per-user |
| Supply-chain firmware attack | Low | Critical | Signature verification + recovery planner |
| Insider threat (declared ownership abuse) | Medium | High | Out-of-band declaration requires file edit or API call |
| Data exfiltration via API | Low | Medium | Local-only by default; no cloud sync without explicit plugin |

## Attack Surfaces

1. **API endpoints** — authenticated by ownership declaration only (honor system).
2. **Serial/USB ports** — physical access required; OS permissions apply.
3. **File system** — firmware images and ownership registry are plaintext JSON.
4. **Knowledge graph DB** — SQLite file; protect with OS-level permissions.

## Assumptions

- The host machine is trusted.
- The user who declares ownership is the legitimate owner (honor system).
- Ed25519 public keys are distributed securely out-of-band.
