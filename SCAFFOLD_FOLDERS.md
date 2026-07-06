# Scaffold Folders

Six folders exist in this repo with no code in them yet: `sdk/`,
`protocols/`, `verification/`, `experiments/`, `benchmarks/`,
`graveyard/`. This file explains why each exists and what it's for —
so "empty folder" doesn't mean "nobody knows why this is here."

Worth naming the tension directly: `DESIGN_PRINCIPLES.md` says "don't
build the empty folder — structure gets added when something real
needs it, not speculatively." These six folders exist anyway, because
an external architecture review specifically recommended them. That's
a deliberate exception, not an oversight — the review's reasoning
(a growing platform needs somewhere for these categories of thing to
eventually live) is sound, but don't take these six as license to
create more speculative folders beyond what's listed here.

## sdk/ (reserved)

Intended eventually for a formal Plugin SDK — a documented, stable
interface external contributors could build plugins against without
reading `plugins/base.py` source directly. Build it when an actual
external contributor needs it, not before.

## protocols/ (reserved)

Intended for wire-protocol specifications once Prometheus needs to
talk to something over a formally-specified protocol, beyond the ad
hoc JSON-over-HTTP the API currently uses or raw serial bytes in
`devices/serial_device.py`. Build against a real protocol need — a
specific device family's actual communication format — not in the
abstract.

## verification/ (reserved)

`engineering/boot_chain.py` and `engineering/crypto_verify.py`
currently hold Prometheus's real verification logic. This folder is
reserved in case verification logic outgrows living inside
`engineering/` — e.g., if verification needs to apply outside Gamma's
specific firmware/boot-chain context. Don't move existing code here
speculatively; `engineering/` is working and tested where it is.

## experiments/

For ideas that aren't ready for an RFC yet — per the external review,
"research projects need somewhere for ideas that aren't ready yet."
Unlike the other reserved folders, this one is meant to be used
casually: a rough script, a half-working prototype, a "what if" that
doesn't deserve RFC-level ceremony. If something here proves out,
promote it to a real RFC and a real module. If it doesn't, leave it
here or move it to `graveyard/`.

## benchmarks/ (reserved)

No part of Prometheus has a performance requirement demanding formal
benchmarking yet — Alpha through Epsilon are all correctness-tested,
not performance-tested. Populate this when an actual performance
question comes up (how many devices can the registry handle, how slow
does twin rebuilding get with a large history) — not before there's a
real question to answer.

## graveyard/

Where abandoned approaches go, with a note on why they were
abandoned — so the same dead end doesn't get re-walked in six months
without anyone remembering it was already tried. Nothing here yet;
Alpha through Epsilon haven't produced a dead end serious enough to
bury yet.
