# Prometheus UI — Implementation Plan

## Goal

Make the `web/` frontend match `C:\Users\josep\Downloads\prometheus_os.html` pixel-by-pixel in structure, styling, and behavior, wired to real backend endpoints.

## Reference

`C:\Users\josep\Downloads\prometheus_os.html` is the source-of-truth for:
- Boot screen: ASCII logo, green OK lines, typing animation, "press any key" skip hint
- Top bar: scaled ASCII brand, connection dot, clock
- Workspace: welcome header, 10-stat grid with pulse bars, dock hint
- Dock: SVG icons + uppercase labels, active state
- Windows: `.pwindow` chrome (purple titlebar bottom-border, yellow title, close hover), draggable, `windowIn` animation
- Terminal: black bar, green log, orange prompt, bottom 90px
- Activity feed: floating top-right toggle
- App content layouts: exact text/rows shown in each window
- Terminal commands: `help`, `show devices`, `connect phone`, `run simulation`, `search firmware`, `recover device`, `explain kernel`, `open <app>`

## Current Gaps

1. **Boot screen** — exists but missing ASCII logo, press-any-key skip, exact boot lines
2. **Top bar** — missing scaled ASCII brand, connection status dots
3. **Stat grid** — missing; workspace only has welcome text
4. **Window chrome** — `.window` styling diverges from `.pwindow` (border, shadow, titlebar purple rule)
5. **Dock** — missing SVG icons, uppercase labels, active state
6. **Activity feed** — missing toggle UI, floating positioning
7. **App mount functions** — all 13 are stubs returning placeholder text
8. **Terminal commands** — only 8 commands; mockup specifies 7 core commands + `open`
9. **Data wiring** — apps show no real fetched data except a few `api.*()` calls

## Implementation Order

1. **Theme fidelity** — update `web/src/theme/crt.css` and `web/src/os/*.ts` to match mockup exactly (`.pwindow`, `#dock`, `#termbar`, `#activity-feed`, pulse animations).
2. **Boot sequence** — rewrite `BootSequence.ts` with ASCII logo, `fadeIn` lines, `press any key` skip, "System Ready" → "Launching Workspace" → transition.
3. **Top bar + workspace** — add scaled ASCII brand, connection dot group, live clock; add 10-stat grid auto-populated from `/status`.
4. **Dock + Activity** — SVG icon set per mockup, uppercase labels, toggleable activity feed populated from SSE `/events`.
5. **Window chrome** — unify `.pwindow` styling, purple titlebar border, draggable, `windowIn` animation, close button hover.
6. **Terminal commands** — implement the 7 mockup commands with corresponding backend calls/logic:
   - `help`, `show devices` (open window), `connect phone` (POST `/devices/simulated`), `run simulation` (open window + POST `/simulation/run`), `search firmware` (GET `/gamma/firmware`), `recover device` (POST `/epsilon/recovery/{id}`), `explain kernel` (GET `/core/status`), `open <app>`
7. **Wired apps** — replace stubs with real data:
   - `KernelApp` → `/core/status`
   - `KnowledgeApp` → `/knowledge/graph` + `/knowledge/timeline`
   - `SimulationApp` → `/simulation/list` + run form
   - `ReasoningApp` → `/observability` + capabilities
   - `HardwareApp` → `/hardware`
   - `DevicesApp` → `/devices`
   - `AgentsApp` → `/agents` with status dots + animated bars for active states
   - `FilesApp` → `/files`
   - `PluginsApp` → `/omega/marketplace/plugins`
   - `MemoryApp` → `/memory`
   - `ActivityApp` → live SSE feed in window
   - `SettingsApp` → sections matching mockup
   - `AssistantApp` → chat UI wired to `/assistant`
8. **Polishing** — ensure pixel borders, `image-rendering: pixelated`, no rounded corners, correct font stack (`Press Start 2P` headings, `VT323` body, `JetBrains Mono` logo), exact hex tokens.

## Backend Needs

Already in place: `/status`, `/core/status`, `/devices`, `/devices/simulated`, `/simulation/run`, `/simulation/list`, `/knowledge/graph`, `/knowledge/timeline`, `/hardware`, `/agents`, `/memory`, `/omega/marketplace/plugins`, `/gamma/firmware`, `/epsilon/recovery/{device_id}`, `/events`.

No new backend endpoints required for the mockup.

## Validation

- `cd web && npm run build` succeeds
- `python -m pytest` still passes (201)
- `uvicorn backend.main:app` → `/dashboard` shows boot → workspace → dock/terminal
- Each dock button opens the matching window with real data
- Terminal commands produce the exact outputs shown in the mockup
- Pressing any key during boot skips to workspace
- Stat grid values come from `/status`
