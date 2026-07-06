# Security Model

Full design rationale is RFC 0000. This is the current-state summary.

## The core decision: declared, not verified

`core/ownership_registry.py` is a persistent, explicit declaration —
`POST /ownership/declare`, or a manual edit to
`config/owned_devices.json`. It is **not** cryptographic or
device-side verification. Every place this fact is surfaced calls it
"declared" — never "verified" — on purpose. RFC 0000 lists the actual
verification approaches (device attestation, manufacturer account
linkage) as unsolved, real engineering problems, not just a "TODO."

## Schema (as of the ownership-schema extension)

```python
{
    "id": "<device_id or disk path>",
    "owner": "<free-text owner name, optional>",
    "declared_at": "<ISO 8601 timestamp>",
    "note": "<free-text>",
    "trust_level": "declared",   # only honest default — see below
    "keys": [],                   # reserved for future public keys
    "certificates": [],           # reserved for future cert chain
    "recovery_policy": null,      # reserved — overrides default RecoveryPlanner rules
}
```

**`trust_level` must never be set to anything stronger than
`"declared"` unless a real mechanism backs it.** `keys` and
`certificates` are reserved fields for the harder verification problem
RFC 0000 describes — populating them today with anything that isn't
real cryptographic material would be actively worse than leaving them
empty, since it would imply a guarantee that doesn't exist.

## Why the flag moved from a URL parameter to a persistent file

Gamma originally accepted `?ownership_declared=true` as a request
parameter — trivially bypassable by anyone who noticed the parameter
name. This was found and fixed during Gamma's own development, not by
an external review: closing a gap like this the moment it's
recognized, rather than leaving it as a known issue, is itself part
of the security model, not a separate housekeeping task.

## What every `engineering/` module and Epsilon's agent must do

Check `is_declared_owned(target)` before acting. `engineering/`
modules are read-only by construction — none of them have a write
path to a real device or disk. Epsilon's `EngineeringReport.deployed`
is hardcoded `False`; there is currently no path from "proposal
passed its tests" to "change applied" (see
`docs/CAPABILITY_BACKLOG.md` — this is a real, open gap, not an
oversight to paper over).

## What's explicitly NOT solved

- Device-side attestation
- Manufacturer account linkage
- A trusted public-key store for Boot Chain Analyzer (currently the
caller must supply the public key directly, every time)
- Any actual deployment/apply mechanism for Epsilon's proposals
