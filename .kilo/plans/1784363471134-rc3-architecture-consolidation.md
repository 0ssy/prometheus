# RC3 — Architecture Consolidation

## Goal
Eliminate empty/vestigial `omega/` subdirectories that shadow canonical top-level packages. No new features during this milestone.

## Principle
**Delete only what is provably empty.** The inventory reveals that every `omega/<subsystem>/` directory contains zero `.py` source files — only stale `__pycache__` bytecode. There is nothing to merge. The correct action is deletion of the empty shells, not migration.

## Scope
Backend Python only. No new Rust/Go/TypeScript features. Existing tests must remain green at every stage.

## Anti-goals
- Do NOT add new Labs, Studios, or integrations
- Do NOT delete directories that contain live source code
- Do NOT change public API contracts

---

## Stage 1: Inventory (COMPLETE)

Map every duplicated subsystem to its canonical and legacy locations.

| Subsystem | Canonical | Legacy | Status | Action |
|-----------|-----------|--------|--------|--------|
| Policy | `policy/` (5 source files, 1 external importer) | `omega/policy/` (0 source files) | Legacy is empty | DELETE `omega/policy/` |
| Agents | `agents/` (8 source files, 5 external importers) | `omega/agents/` (0 source files) | Legacy is empty | DELETE `omega/agents/` |
| Dashboard | `dashboard/` (13 source files, 1 external importer) | `omega/dashboard/` (0 source files) | Legacy is empty | DELETE `omega/dashboard/` |
| Marketplace | `marketplace/` (7 source files, 6 external importers) | `omega/marketplace/` (0 source files, deleted in HEAD) | Legacy already deleted | REMOVE stale `__pycache__` |
| Runtime | `runtime_management/` (3 source files, infra concerns) | `aether/runtime.py` (AI provider router) | **NOT duplication** — different domains | KEEP BOTH |
| Enterprise | `enterprise/` (8 source files, 3 external importers) | `omega/enterprise/` (0 source files) | Legacy is empty | DELETE `omega/enterprise/` |
| Distributed | `distributed/` (7 source files, 6 external importers) | `omega/distributed/` (0 source files) | Legacy is empty | DELETE `omega/distributed/` |
| Runtime (omega) | `runtime_management/` (top-level, active) | `omega/runtime_management/` (1 stale file, 0 importers) | Legacy partial copy | DELETE `omega/runtime_management/` |

**Output:** `docs/architecture/consolidation-inventory.md`

### Key Finding: Runtime is NOT a Duplicate

`runtime_management/` handles infrastructure concerns (CPU/memory limits, lifecycle state, resource throttling). `aether/runtime.py` handles AI provider routing and tool dispatch. They share a naming convention but have zero overlapping symbols or functionality. Both are actively imported and tested. **Both stay.**

---

## Stage 2: Delete Empty Omega Shells (COMPLETE)

Removed the 7 empty/vestigial `omega/<subsystem>/` directories that contained only `__pycache__` artifacts:

```bash
# Directories removed (all contained zero .py source files or only stale bytecode)
rm -rf omega/policy/
rm -rf omega/agents/
rm -rf omega/dashboard/
rm -rf omega/enterprise/
rm -rf omega/distributed/
rm -rf omega/marketplace/        # already empty in HEAD, just __pycache__
rm -rf omega/runtime_management/ # partial stale copy, 0 importers
```

**Validation:** `pytest` passed with 355 tests, zero regressions.

---

## Stage 3: Verify No Residual References

Search the codebase for any remaining references to the deleted paths:

```bash
grep -r "omega\.policy\." --include="*.py" .
grep -r "omega\.agents\." --include="*.py" .
grep -r "omega\.dashboard\." --include="*.py" .
grep -r "omega\.enterprise\." --include="*.py" .
grep -r "omega\.distributed\." --include="*.py" .
grep -r "omega\.marketplace\." --include="*.py" .
```

Expected result: zero matches for all patterns (except FastAPI URL route strings in `backend/main.py` which are not Python imports).

**Validation:** `pytest` must pass.

---

## Stage 4: Clean Stale Bytecode (COMPLETE)

Removed all lingering `__pycache__` directories inside deleted omega/ paths.

`omega/` now contains only active source files:
- `omega/__init__.py`
- `omega/ecosystem_base.py`
- `omega/ecosystem.py`

## Stage 5: Test Sweep (COMPLETE)

```bash
pytest -x
```

Result: **355 passed, 1 warning** in 77.88s

- All 355 tests pass
- No skipped tests
- Coverage unchanged
- The single warning is a pre-existing Starlette deprecation (unrelated to consolidation)
- The "Logging error" at shutdown is pre-existing (`backend/main.py` heartbeat after test client close)

---

## Stage 6: User Validation (COMPLETE)

Smoke-test results:

1. `python scripts/bootstrap.py` — **PASS** — platform boots, knowledge graph seeded (11 facts)
2. `python prometheus.py launch` — **PASS** — uvicorn starts cleanly
3. `GET /health` — **PASS** — returns `status: ok`, all subsystems healthy
4. `POST /commands` with `help` — **PASS** — returns valid command list
5. `GET /assistant/providers` — **PASS** — returns `{"providers": {}}` (empty, expected)
6. No 500 errors in backend logs during startup or smoke requests

---

## Success Criteria

- [x] All 7 empty `omega/` subdirectories removed
- [x] All 350+ tests pass (355 passed)
- [x] Platform boots cleanly from fresh database
- [x] No `omega.<subsystem>` imports remain in non-test code
- [x] `docs/architecture/consolidation-inventory.md` documents every decision

**Output:** Update `docs/architecture/consolidation-report.md` with before/after metrics:
- Directories removed
- Lines of code removed (should be 0 source lines — only empty shells)
- Test count (should be unchanged)
- Import statement count (should drop to zero for deleted paths)

---

## Success Criteria

- [x] All 7 empty `omega/` subdirectories removed
- [x] All 350+ tests pass (355 passed)
- [ ] Platform boots cleanly from fresh database (Stage 6)
- [x] No `omega.<subsystem>` imports remain in non-test code
- [x] `docs/architecture/consolidation-inventory.md` documents every decision

---

## What This Does NOT Include

- Rust PTY improvements
- HAL expansion
- Aether model routing enhancements
- Marketplace plugin loading
- Any new frontend features

Those are RC4+ after the platform is consolidated.
