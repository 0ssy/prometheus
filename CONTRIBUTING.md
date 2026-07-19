# Contributing to Prometheus

Thanks for contributing. This project values architecture discipline,
safety, and long-term maintainability over short-term speed.

## Coding conventions

- Keep modules focused; avoid cross-layer coupling.
- Reuse existing contracts (`Device`, plugin/agent base classes) instead of
  introducing parallel abstractions.
- Prefer explicit error handling; no silent fallbacks.
- Keep naming clear and domain-oriented.
- Add tests or at least test scaffolding for behavior changes.

## Placement rules (discoverability)

Before creating a new top-level folder, map your change to an existing area:

- Runtime foundations -> `core/`
- HTTP/API behavior -> `backend/`
- Orchestration logic -> `services/`
- Hardware capabilities (USB/Serial/Bluetooth/JTAG/...) -> `hardware/`
- Firmware behavior -> `firmware/`
- Intelligence layers -> `knowledge/`, `memory/`, `simulation/`
- Extensions -> `plugins/`, `agents/`, `sdk/`
- UI -> `web/`, `src-tauri/`

If none fit, open an RFC before introducing a new top-level namespace.

## Branch strategy

- `main` is the integration branch.
- Use short-lived feature branches for substantial work.
- Keep changes scoped and coherent (one concern per branch when possible).

## RFC workflow

Use RFCs for significant design or behavior changes:

- New subsystem or major interface changes
- Security model changes
- Changes with long-term architectural impact

RFCs describe proposals and alternatives before implementation.

## ADR workflow

Use ADRs for decisions that are now adopted:

- Record what was chosen and why
- Link to relevant RFC(s)
- Note consequences and trade-offs

ADRs live in `architecture/adr/` and should be updated when decisions evolve.

## Commit message style

- Use clear, imperative summaries:
  - `Add ownership trust-level fields`
  - `Refactor startup into core bootstrap`
- Include a short body when context is important.
- Keep unrelated changes in separate commits.

## Pull request expectations

- Explain intent, scope, and risk.
- Link RFC/ADR where relevant.
- Include verification evidence (tests, endpoint checks, or command output).
- Avoid mixing refactors with feature changes unless required.

## Definition of done

- Architecture boundaries remain clear.
- Behavior is verified.
- Documentation is updated for user-visible or architecture-level changes.
