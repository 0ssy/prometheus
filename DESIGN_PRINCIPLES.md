# Prometheus — Design Principles

Not technical documentation — principles. When an RFC or a line of
code seems to conflict with one of these, that's a signal to stop and
resolve the conflict deliberately, not to quietly pick whichever is
more convenient that day.

- **Build for decades, not demos.** Every phase so far (Alpha through
  Epsilon) was tested against something real — a real GPT disk, a
  real Ed25519 signature, a real fault injection — before being called
  done. A demo that only works on the happy path isn't done.

- **Prefer verification over assumption.** Gamma's Boot Chain Analyzer
  does real cryptographic verification, not a mocked pass/fail. When a
  module can't verify something, it says `"unknown"` — it doesn't
  guess and call the guess a result.

- **Every subsystem should be replaceable.** `Device` is one interface
  that `SimulatedDevice` and `SerialDevice` both implement identically
  from the outside. A plugin or agent written against the interface
  doesn't care which one it's actually talking to.

- **Plugins and agents are first-class citizens**, not afterthoughts
  bolted onto a core. `plugins/` and `agents/` existed from Phase
  Alpha, before there was anything to plug into hardware.

- **Security by design, not by patch.** RFC 0000's ownership gate
  was built into Gamma from its first line of code, not added after
  a review found the gap. When Gamma's original ownership flag turned
  out to be too easy to bypass (a URL query parameter), it was
  replaced with a persistent, deliberate declaration — closing a real
  gap is part of the design process, not an emergency afterward.

- **Owner-controlled recovery only.** Every Gamma and Epsilon module
  that touches a device or proposes a change checks
  `ownership_declared` first. This is stated as a binding scope
  constraint in RFC 0002, not a preference.

- **Simulation before action, always.** `SimulatedDevice`,
  `SimulatedFirmwareDevice`, and Epsilon's `simulate_proposal()` all
  exist so nothing gets built or tested against real hardware first.

- **Record architectural decisions.** That's what `RFCs/` is for.
  An RFC's status line should always reflect reality, not sit stale
  once code exists.

- **Honesty in what a system claims about itself.** `ownership_declared`
  is called "declared", never "verified", everywhere it appears. A
  `trust_level` field that implies a guarantee stronger than what
  actually backs it is worse than no field at all.

- **A whitelist grows deliberately, one entry at a time.** Epsilon's
  `SUPPORTED_CHANGE_TYPES` started with exactly one entry on purpose.

- **Don't build the empty folder.** Structure gets added when
  something real needs it, not speculatively, in advance.

- **Knowledge is immutable; understanding evolves.** Do not delete or
  overwrite historical facts. Record new evidence with confidence and
  provenance, then derive current belief from the full history.
