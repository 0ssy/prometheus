# PROMETHEUS Engineering Intelligence OS — Front-End Implementation Plan

## Goal

Replace the single-file `backend/dashboard.py` HTML template with a real **front-end operating environment**: a pixel/CRT "engineering workstation" with an ASCII boot sequence, a windowed desktop (13 running applications in movable/resizable pixel windows), a persistent bottom terminal, and a live activity feed. It must feel like an OS, not a SaaS dashboard, and must be **wired to the real PROMETHEUS backend** (not mock data).

## Resolved Decisions

- **Stack:** Vanilla **TypeScript + Vite** (no React). Node v24 is available. Vite gives modularity + a build step while preserving full control over the pixel aesthetic and honoring the master prompt's "NOT React / not a website" intent.
- **Scope:** All **13 applications full fidelity** (Kernel, Knowledge, Simulation, Reasoning, Hardware, Devices, Agents, Files, Plugins, Memory, Activity, Settings, Assistant).
- **Data:** **Wire to the real backend** and extend the API where needed (live agent status, knowledge-graph nodes/edges, simulation list, files browser, etc.). Terminal commands call real endpoints.

## Current Backend Surface (already usable)

`backend/main.py` exposes: `/health`, `/status`, `/stats`, `/events` (SSE), `/core/status`, `/observability`, `/capabilities` (+execute/history), `/memory` (GET/POST), `/knowledge` (GET/POST), `/devices` (+register/write/disconnect), `/ownership`, Gamma/Delta/Epsilon/Omega endpoints (firmware, diagnostics, recovery, digital twin, marketplace, policy, agents coordination). `dashboard/` Python package gives JSON section views via `GET /omega/dashboard/{section}`.

Gaps to fill (see Backend Extensions): live **agent status**, real **knowledge-graph** topology (currently randomly generated client-side), **simulation** run/list, **files** browser, **hardware** HAL snapshot, **assistant** endpoint.

## Project Layout

Create a new `web/` front-end project at repo root:

```
web/
  index.html                 # Vite entry (mounts #os-root)
  vite.config.ts             # build -> web/dist; dev proxy / -> http://127.0.0.1:8000
  tsconfig.json
  package.json               # vite, typescript, (no UI framework)
  src/
    main.ts                  # bootstraps OS: boot screen -> desktop -> window manager
    theme/
      tokens.css             # exact palette as CSS vars (see Design System)
      fonts.css              # @font-face for pixel fonts
      crt.css                # scanline/CRT overlay, pixel borders, animations
    os/
      Desktop.ts             # topbar (wordmark, connection, health, clock), center, dock
      WindowManager.ts       # create/focus/min/max/close, drag, resize, persist positions
      Window.ts              # pixel window chrome (titlebar + ▢▣✕ controls)
      Dock.ts                # app launchers + open-window indicators
      StatusBar.ts           # bottom system status (kernel/devices/agents/latency/version)
      Store.ts               # global live snapshot state + SSE subscription
    boot/
      BootSequence.ts        # fullscreen ASCII boot, typewriter, optional "stay in Terminal Mode"
    terminal/
      Terminal.ts            # always-visible REPL at bottom, blinking cursor, history
      commands.ts            # command registry (GUI-action mirrors)
    api/
      client.ts              # typed fetch wrappers for every endpoint
      events.ts              # SSE wrapper over /events
    apps/
      App.ts                 # interface: { id, title, icon, mount(root), tick?(), destroy?() }
      KernelApp.ts  KnowledgeApp.ts  SimulationApp.ts  ReasoningApp.ts
      HardwareApp.ts DevicesApp.ts   AgentsApp.ts      FilesApp.ts
      PluginsApp.ts  MemoryApp.ts    ActivityApp.ts    SettingsApp.ts  AssistantApp.ts
```

## Design System (exact tokens)

CSS variables (from master prompt):
`--bg:#0D1117; --panel:#161B22; --border:#2A3441; --text:#F5F5F5; --muted:#A8A8A8; --yellow:#F2C230; --orange:#F2911D; --orange-red:#F24F13; --steel:#8082A6; --purple:#46334F;`

- **Fonts:** Headings = *Press Start 2P* (Google Fonts). Body/terminal = *VT323* + *Departure Mono* / *Px437* (Google Fonts has VT323 + Press Start 2P; self-host Departure Mono/Px437 via `@font-face` with `monospace` fallback). No glassmorphism, no rounded SaaS cards, no gradients-as-decoration, no big whitespace.
- **Borders:** stepped pixel borders via `box-shadow`/`border-image`, sharp corners (0 radius), 1px `--border`.
- **Motion:** subtle + engineered — blinking terminal cursor, agent "pulse" while Thinking, knowledge-graph node drift, simulation progress, live clock. No flashy transitions.
- **Identity:** wordmark `PROMETHEUS` is the brand; no icon/flame/mascot.

## Backend Extensions (in `backend/main.py` + helpers)

1. **Agents live status** — add a `status` map to `AgentManager` (set `thinking`/`idle`/`running` on dispatch/perform; `learning` for MemoryAgent, etc.) and emit `agent.status` events on the bus. New `GET /agents` returns `[{name, status, last_task, updated_at}]`. (`agents/manager.py` currently only has `list_agents()` returning names — extend it.)
2. **Knowledge graph** — new `GET /knowledge/graph` returning `{nodes:[{id,label,type,confidence}], edges:[{source,target,relation}]}` from the real knowledge engine/graph; plus `GET /knowledge/timeline` and reuse `/knowledge` for facts/provenance/ontology. Replace client-side random graph.
3. **Simulation** — new `POST /simulation/run` (device_id, failure_mode) calling `SimulationEngine.simulate` and storing a run record; `GET /simulation/list` returns runs with progress/risk/confidence. Digital-twin viz reuses `GET /delta/twin/{device_id}`.
4. **Files** — new `GET /files?path=...` listing a configured workspace root (default `./workspace/` with `Projects/ Research/ Datasets/ Models/ Plugins/ Agents/ Digital Twins/ Simulations/ Recovered Devices/ Exports/`). **Must sanitize paths (block `..`/absolute traversal) and confine to root.** Seed these dirs if missing.
5. **Hardware** — new `GET /hardware` snapshot aggregating `/epsilon/hal/interfaces`, diagnostics, battery, firmware into one live payload.
6. **Assistant** — new `POST /assistant` that routes a prompt to an agent dispatch (or capability) and streams/returns the result; terminal `explain kernel`, `help`, etc. map here. (Clarify LLM availability — see Open Questions.)
7. **Serve the SPA** — keep `mount_dashboard` but serve the Vite `web/dist` build: `/dashboard` returns `index.html`; add a static mount for `/dashboard/assets/*`. In dev, run `vite` (port 5173) with proxy `/`→`8000`; do not break `/docs`.

No breaking changes to existing endpoints; all additions are new routes.

## The 13 Applications (data source → behavior)

- **Kernel** — `/core/status`, `/status`(kernel). Live health dot, uptime, subsystem list. `explain kernel` terminal cmd.
- **Knowledge** — `/knowledge/graph` (animated nodes/edges), `/knowledge` facts, provenance, timeline, ontology browser, search. Click node → facts panel.
- **Simulation** — `/simulation/list` + `POST /simulation/run`; progress bars, risk/confidence, digital-twin viz (`/delta/twin`), scenario compare.
- **Reasoning** — `/core/status`(reasoning), `/knowledge` facts with confidence, reasoning pipeline status. `show reasoning`.
- **Hardware** — `/hardware` snapshot: USB/BT/network/sensors/battery/firmware/capabilities, live updates. `show devices`.
- **Devices** — `/devices`, `/devices/{id}`, register/write/disconnect. `connect phone`, `recover device`.
- **Agents** — `/agents` (live status: Thinking/Idle/Learning/Running/Connected) + `/events`. Pulsing while Thinking. `dispatch <agent>`.
- **Files** — `/files` browser (real FS under workspace root). Double-click opens file in a window.
- **Plugins** — `/health`(plugins_loaded), `/omega/marketplace/plugins`, `POST /plugins/{name}/run`. `list plugins`.
- **Memory** — `/memory` GET/POST; tag filter. `remember <text>`.
- **Activity** — `/events` SSE live feed (kernel started, device connected, fact asserted, …). `activity`.
- **Settings** — Models/Plugins/Memory/Appearance/Hardware/Networking/Security/Permissions/Updates/Extensions. Read from `/health`, `/capabilities`, config; Appearance persists to `localStorage` (theme tokens swap).
- **Assistant** — chat REPL → `POST /assistant`; shows agent responses; also drives terminal-style natural commands.

## Terminal Command System

`terminal/commands.ts` registers commands; each GUI action has a terminal equivalent:
`help, connect <device>, run simulation <device> <mode>, show devices|kernel|agents|plugins|reasoning, search firmware <path>, recover device <id>, explain <subsystem>, remember <text>, dispatch <agent> <task>, activity, files [path], settings <section>, clear`.
Parser issues real `api/client.ts` fetches; output rendered in the always-visible bottom terminal. Opening any app is also reachable via command (e.g. `open knowledge`).

## Build / Serve Integration

- `web/package.json`: `dev` (vite), `build` (vite build → `web/dist`), `typecheck` (tsc --noEmit), `lint` (eslint).
- `vite.config.ts`: `base: '/dashboard/'`, dev server proxy `/` → `http://127.0.0.1:8000`.
- `backend/main.py`: serve `web/dist` at `/dashboard` (+ `/dashboard/assets`), fall back to `index.html` for client routes. Keep `/docs`.
- README: update "Engineering dashboard" run instructions (build web, run api).

## Validation / Acceptance

1. `cd web && npm install && npm run typecheck && npm run lint && npm run build` succeed.
2. `python -m pytest` still passes (no backend regressions).
3. `uvicorn backend.main:app` → `http://127.0.0.1:8000/dashboard` shows ASCII boot, optionally stays in Terminal Mode, then transitions to the desktop.
4. All 13 apps launch from the dock as draggable/resizable pixel windows; multiple stay open; positions persist across reloads.
5. Kernel/Knowledge/Agents/Devices/Activity update live (polling `/status` + `/events` SSE); knowledge graph shows real nodes from `/knowledge/graph`.
6. Bottom terminal is always visible; `help`, `connect phone`, `run simulation`, `show devices`, `recover device`, `explain kernel` all work and mirror GUI actions.
7. Files browser lists the seeded workspace tree without escaping its root.

## Risks

- **Scope:** all-13 full fidelity is large; build incrementally (shell → core apps → remaining) but plan covers all.
- **Font licensing:** Departure Mono/Px437 may need self-hosted files; fall back to VT323/monospace if unavailable.
- **File browser security:** strict path confinement required (no traversal).
- **Live agent status** requires `AgentManager` changes — coordinate with backend owner.

## Open Questions (not blocking; resolve during build)

1. **Assistant LLM:** is there an API key/model configured for the Assistant, or should it route to local agent dispatch only?
2. **Files root:** confirm default workspace path and whether user files should live under repo `./workspace/`.
3. **Appearance persistence:** client-side `localStorage` (recommended) vs server-side per-user setting (no auth/user system yet).
