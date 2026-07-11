# Prometheus RC1 Hardening Checklist

Status: Draft  
Target tag: `v1.0.0-rc1`

## Scope freeze

RC1 accepts:

- Bug fixes
- Performance improvements
- Documentation updates
- Packaging and installer fixes
- Cross-platform fixes (Windows + Linux)

RC1 rejects:

- New features
- API contract changes unless required for a bug fix
- Large refactors not tied to reliability/performance

## Execution order with pass gates

### 1) Stabilization baseline

- [ ] Confirm branch is up to date and CI is green
- [ ] Run full backend tests (`pytest`)
- [ ] Run frontend quality gates (`npm run typecheck`, `npm run lint`, `npm run build` in `web/`)
- [ ] Record baseline numbers (test pass count, build duration, bundle size)

Gate: all baseline checks pass on maintainer machine.

### 2) Bug-fix-only window

- [ ] Fix only user-visible defects and high-confidence regressions
- [ ] Require a regression test for each fixed defect when practical
- [ ] Keep changes small and reviewable
- [ ] Re-run targeted tests per fix before merge

Gate: no open P0/P1 bugs for RC1 scope.

### 3) Performance hardening

- [ ] Re-run existing benchmark scripts in `benchmarks/`
- [ ] Compare against baseline and verify no major regressions
- [ ] Validate startup responsiveness and dashboard responsiveness on realistic data volumes
- [ ] Verify memory growth remains bounded in common workflows

Gate: no blocker-level perf regressions vs baseline.

### 4) Packaging and installer verification

RC1-supported installer (verified): the Python path —
`pip install -r requirements.txt` then `python prometheus.py`. This is
covered by `tests/test_installer_smoke.py` and the clean-install boot check.

Desktop installer (verified): the Tauri package in `src-tauri/` builds and
produces an NSIS installer
(`src-tauri/target/release/bundle/nsis/Prometheus_0.6.0_x64-setup.exe`).
Requires Rust + WebView2 + NSIS on the build host; config
(`tauri.conf.json` NSIS target, icons, `beforeDevCommand`) and
prerequisites are documented in `src-tauri/README.md`.

- [x] Build Tauri desktop package from `src-tauri/` (Rust + WebView2 + NSIS)
- [ ] Validate installer output integrity (install completes, uninstall works)
- [ ] Verify first-run startup path on clean machine profile
- [ ] Verify safe behavior on missing/corrupted local DB

Gate: Python install + first-run + uninstall succeed (verified). Tauri NSIS
build succeeds and the installer artifact is produced (verified). Remaining
items (install/uninstall run-through, first-run on clean profile) are
manual QA before the `v1.0.0-rc1` tag.

### 5) Cross-platform validation

- [ ] Run full verification matrix on Windows
- [ ] Run full verification matrix on Linux
- [ ] Validate shell/paths/process behavior for both platforms
- [ ] Validate plugin crash isolation and API availability on both platforms

Gate: required matrix passes on both platforms.

### 6) Documentation freeze pass

- [ ] Update README run/build/release instructions if changed
- [ ] Update CHANGELOG with RC1 hardening highlights
- [ ] Ensure architecture docs match shipped behavior
- [ ] Provide known limitations and workaround notes

Gate: docs align with actual shipped behavior.

### 7) External UAT pass

- [ ] Distribute RC1 build to a small external tester set
- [ ] Collect install/run/upgrade feedback
- [ ] Triage issues by severity and fix blocker defects only
- [ ] Confirm no release blockers remain

Gate: external testers complete core workflows without blockers.

### 8) Final release candidate cut

- [ ] Freeze branch for final RC1 validation
- [ ] Run full test + lint + build one final time
- [ ] Tag release candidate: `v1.0.0-rc1`
- [ ] Push tag and publish release notes
- [ ] Create next branch for AI runtime work: `feature/ai-runtime-rust`

Gate: tag is published and reproducible from source.

## Minimum verification commands

From repository root:

```bash
pytest
```

From `web/`:

```bash
npm run typecheck
npm run lint
npm run build
```

From `src-tauri/`:

```bash
cargo tauri build
```

## Exit criteria for starting Project Aether

Start Rust AI runtime work only after all conditions are true:

- [ ] RC1 checklist gates are complete
- [ ] `v1.0.0-rc1` tag exists on remote
- [ ] Mainline branch is stable and green
- [ ] AI runtime work starts on isolated branch (`feature/ai-runtime-rust`)
