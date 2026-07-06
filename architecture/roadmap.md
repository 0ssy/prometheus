# Roadmap

## Where things actually stand

| Phase | Module | Status |
|---|---|---|
| Alpha | `core/`, `agents/`, `plugins/`, `memory/`, `reasoning/` | Done |
| Beta | `devices/` | Done — real-hardware serial test still pending |
| Gamma | `engineering/` (renamed from `gamma/`) | Done, v0.1 |
| Delta | `digital_twin/` (renamed from `delta/`) | Done |
| Epsilon | `autonomous/` (renamed from `epsilon/`) | Done, v0.1 — one whitelisted change type, no deploy path |

## Beyond Epsilon (from the original doodle roadmap)

- **Robotics & Labs** — not started, not designed
- **"Prometheus OS"** — renamed to **Prometheus Platform** per
  external review (it's not trying to replace an operating system;
  "platform" is the more accurate and more flexible framing) — not
  started, and honestly a long way off

## Near-term real next steps

These are concrete, not aspirational — see
`docs/CAPABILITY_BACKLOG.md` for the full list with the
limitation/why/extension format:

1. Real ESP32 test against `SerialDevice` — blocked on hardware
   arriving, not on any design work
2. Epsilon deployment mechanism — a human-gated
   `/epsilon/apply/{proposal_id}` that applies exactly the one
   narrow change a passed proposal described
3. MBR partition parsing (Gamma currently detects but doesn't parse
   MBR disks)
4. A trusted public-key store for Boot Chain Analyzer

## Principle for adding anything beyond this list

Per `DESIGN_PRINCIPLES.md`: don't build the empty folder, don't design
the abstract solution before there's a second real case to test it
against. Multi-device twin relationships, additional Epsilon change
types, and device-side attestation are all real future work — but
each should get designed against an actual concrete need (a second
real device, a second real proposal type) rather than speculatively
in advance.
