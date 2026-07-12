# RC1 Hardening Plan

Target: close all unchecked items in `docs/release/rc1-checklist.md` so the
`v1.0.0-rc1` tag can be cut from a stable, green mainline.

**Open decision:** The checklist specifies tag `v1.0.0-rc1`, but the repo already
contains a `v0.5.0-rc1` tag. My recommendation is to follow the checklist
literally and target `v1.0.0-rc1` (the existing `v0.5.0-rc1` was an earlier
release-candidate attempt; the current changelog explicitly scopes a new
RC1 hardening pass under `[Unreleased]`). Confirm before tagging.

---

## Step 1 — Stabilization baseline
1. Fix frontend install: `web/node_modules` is missing `typescript` and `vite`
   (verified via `npm ls —depth=0`). Run `npm ci` in `web/` to restore a
   complete node_modules.
2. Run full backend tests: `pytest` (224 tests, currently passing).
   Record pass count and duration as the RC1 baseline.
3. Run frontend gates in `web/`: `npm run typecheck`, `npm run lint`,
   `npm run build`. These currently fail because `tsc` is unavailable.
4. Record bundle size (`web/dist/` asset count/size) and build duration.
5. Confirm `backend/main.py` uses `on_event("startup")` (current) or migrate to
   `lifespan` handlers to silence the FastAPI deprecation warnings that CI
   emits today.

**Blocker:** Frontend node_modules must be restored before any frontend gate
can pass.

## Step 2 — Bug-fix-only window
- No open P0/P1 bug tracker is configured in this repo (no issues doc, no
  GitHub project, no `P0`/`P1` labels found). Treat any CI failure in Step 3
  as a de-facto regression. Add regression tests for each fix at time of
  repair.
- Known risk to cover:
  * `backend/main.py:81` FastAPI `on_event` deprecation — add lifespan
    handlers before RC1 or document as deferred.
  * `src-tauri/tauri.conf.json` hardcodes Windows paths in
    `beforeBuildCommand` (`venv\Scripts\python.exe`). Block Tauri build on
    non-Windows hosts if cross-platform desktop is in scope.

## Step 3 — Performance hardening
1. Populate `benchmarks/`:
   - `benchmarks/boot/benchmark_boot.py` — measure `prometheus.py --server`
     start to `/health` first 200 (similar to `performance.yml` workflow).
   - `benchmarks/memory/benchmark_memory.py` — measure RSS after startup and
     after 100 API calls.
2. Add `benchmarks/README.md` with `python benchmark_boot.py` and
   `python benchmark_memory.py` commands.
3. Re-run `pytest tests/test_knowledge_graph_scaling.py
   tests/test_simulation_engine.py tests/test_plugin_manager.py --durations=0`
   as the targeted perf gate.
4. Gate: no test duration regression > 20% vs recorded baseline; memory < 350
   MB; boot < 5 s.

## Step 4 — Packaging and installer verification
**Python path (already good):**
- `tests/test_installer_smoke.py` covers clean-venv boot + corrupted DB
  quarantine. Keep passing.

**Tauri NSIS path ( Windows only in current config ):**
1. `src-tauri/tauri.conf.json` `beforeBuildCommand` hardcodes a Windows
   venv path. Replace with a script (`scripts/pre_tauri_build.py`) that locates
   the Python exe cross-platform, or document the Windows-only requirement in
   `src-tauri/README.md`.
2. Built artifact check: after `cargo tauri build`, verify
   `src-tauri/target/release/bundle/nsis/Prometheus_0.6.0_x64-setup.exe`
   exists.
3. Install/uninstall smoke on a local or VM Windows host:
   - Run installer, verify `/health` reachable on `127.0.0.1:8000`.
   - Uninstall, verify no orphaned processes or data.
4. First-run on clean profile: remove `data/prometheus.db`, reinstall, verify
   fresh DB is created on first boot.
5. Missing/corrupted DB: `tests/test_database_corruption_recovery.py` covers
   the quarantine-and-recreate path. Add an integration test that exercises it
   through the running server if not already present.

**Gate:** Python install boot + corrupted DB recovery pass. Tauri NSIS build
succeeds and installer artifact is produced. Install/uninstall run-through is
manual QA.

## Step 5 — Cross-platform validation
1. Ensure CI matrix covers:
   - `ubuntu-latest` + `windows-latest` for `pytest` + health check
     (`ci.yml`, `windows.yml`, `linux.yml` already exist).
   - Add a Linux workflow that also boot checks `/health` from
     `python prometheus.py --server` with `curl` (mirror of `linux.yml`).
2. Add Linux Tauri build job only if desktop packaging for Linux is in scope.
   Today `tauri.conf.json` targets NSIS only; adding `appimage` or `dmg`
   requires setting `bundle.targets` per-platform and building on the
   respective OS. **Recommend out-of-scope for RC1** — document as post-RC.
3. Plugin crash isolation is already covered by tests
   (`test_plugin_manager.py::test_run_isolates_plugin_exception`,
   `test_run_publishes_error_event_on_crash`, `test_run_timeout_aborts_hung_plugin`).
   Verify these run on both OS runners in CI.

**Gate:** All OS runners green in GitHub Actions.

## Step 6 — Documentation freeze pass
1. `README.md` Quickstart + run/build/release instructions already updated
   (per CHANGELOG). Verify all `curl` examples and Windows/Unix paths are
   accurate.
2. `CHANGELOG.md` already lists RC1 hardening highlights. Add a date stamp
   and link to the `v1.0.0-rc1` tag in the `[Unreleased]` header note.
3. `ARCHITECTURE_DECISION_LOG.md` and `docs/architecture/*.md`: scan for
   references to renamed or removed modules (e.g. `omega/ecosystem.py`,
   `epsilon/hal.py` scaffolding vs current `hardware/hal/` paths). Fix
   discrepancies.
4. Add `KNOWN_LIMITATIONS.md` (or a section in `README.md`) covering:
   - Linux desktop installer not yet packaged (Windows NSIS only).
   - `on_event` deprecation pending migration to lifespan.
   - Ontology in-memory only; no DB migration system.
   - Dynamic plugin discovery not yet implemented.

**Gate:** Docs verified against `git ls-files` + running server endpoints.

## Step 7 — External UAT pass
1. Distribute RC1 build:
   - Python path: pip-installable `requirements.txt` (no `pyproject.toml`
     installation registered; add `pip install -e .` support if needed, or
     document direct `requirements.txt` + `python prometheus.py` as the
     verified installer).
   - Windows NSIS installer artifact from Step 4.
2. Collect feedback via a shared form or issue template. Triage new findings
   into a simple `P0`/`P1` shortlist; fix only blocker defects before cut.
3. Confirm no release blockers remain.

**Gate:** External tester core workflows (health, plugin run, agent dispatch,
knowledge query, dashboard load) all succeed without blockers.

## Step 8 — Final release candidate cut
1. Freeze branch for final validation: run `pytest`, frontend gates,
   performance benchmarks, and both OS CI jobs one final time on a clean
   `main`.
2. Tag: `git tag v1.0.0-rc1 && git push origin v1.0.0-rc1`.
3. Publish release notes:
   - `softprops/action-gh-release` (already wired in `.github/workflows/release.yml`)
     will auto-publish a GitHub Release on tag push.
   - Append the RC1 hardening highlights to `CHANGELOG.md` under
     `## [v1.0.0-rc1] - YYYY-MM-DD`.
4. Create `feature/ai-runtime-rust` branch from `main` for post-RC work.

**Gate:** Tag exists on remote, release is published, main is stable and green.

---

## Execution order (critical path)

```
Step 1 (baseline) →
  Step 2 (regressions) →
    Step 3 (perf) →
      Step 4 (installer) →
        Step 5 (cross-platform CI) →
          Step 6 (docs) →
            Step 7 (UAT) →
              Step 8 (tag)
```

Step 3 and Step 4 can run in parallel once Step 2 is clear.
