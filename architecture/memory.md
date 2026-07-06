# Memory

Two genuinely different things live under "memory" in this project —
worth keeping them conceptually separate even though both are Phase
Alpha deliverables.

## Long-term memory (`memory/store.py`)

Free-text entries with a tag, stored via `remember()`/`recall()`.
This is unstructured — a note, an observation, anything that doesn't
fit as a subject/predicate/object fact. Think of it as Prometheus's
scratchpad, not its source of truth about device state.

## Knowledge graph (`reasoning/`)

Structured facts: `subject`, `predicate`, `object`, timestamped,
append-only (`assert_fact()` never updates or deletes). This is the
actual source of truth every phase above Alpha reads from:

- Beta writes `connected` / `disconnected` / `wrote` events
- Gamma writes `partition_table_read:*`, `firmware_inspected:*`,
  `boot_chain:*` events
- Delta reads all of the above to build a `DeviceTwin` — it writes
  nothing new
- Epsilon reads a twin (via Delta) and writes one
  `engineering_proposal_evaluated:*` fact per proposal it evaluates

**Append-only is a real property, not incidental.** Delta's History
field works specifically because nothing in the fact store gets
overwritten — see `digital_twin/twin.py`'s docstring. If a future
change ever needs to *update* a fact rather than append a new one,
that's a design decision serious enough to need its own RFC, not a
quiet addition to `reasoning/graph.py`.

## What's NOT here yet

No working memory / short-term context distinct from the permanent
knowledge graph. No memory expiry or pruning — the graph grows
forever right now. Not a problem yet at this scale; see
`docs/CAPABILITY_BACKLOG.md` if it becomes one.
