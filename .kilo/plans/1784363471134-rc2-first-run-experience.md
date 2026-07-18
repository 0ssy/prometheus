# RC2 — First-Run Experience

## Goal
Turn "platform works but feels empty on first launch" into "platform is usable in 60 seconds."

## Scope
Frontend UX, backend onboarding API, seed data, README split, CLI launcher.
No new Rust/Go distributed features.

## Tasks

### 1. AI Provider Onboarding (P0)
**Files:** `backend/main.py`, `services/llm_client.py`, `web/src/apps/AssistantApp.ts`, `web/src/sdk/assistant.ts`

- Add `GET /assistant/providers` that returns available provider templates (LM Studio, Ollama, OpenAI, Gemini, OpenRouter) plus current config status.
- Add `POST /assistant/providers` to save a provider config (base_url, model, api_key) to `core/config.py` (or a new `~/.prometheus/providers.json`).
- Frontend `AssistantApp.ts`: when no providers are configured, show the onboarding card instead of the chat UI.
  - Card: "No language model is configured."
  - Buttons for each provider template with pre-filled defaults.
  - "Continue without AI" hides the assistant app from the dock.
- `LLMClient.is_configured()` stays the same; the endpoint just makes it discoverable.

### 2. One-Command Bootstrap (P0)
**Files:** `scripts/bootstrap.py` (new), `README.md`

- Create `scripts/bootstrap.py` that:
  1. Checks Python >= 3.11
  2. Creates venv `.venv/`
  3. Installs `requirements.txt`
  4. Runs `npm install` in `web/` if Node is present
  5. Runs `npm run build` in `web/`
  6. Prints "Run `python prometheus.py launch`"
- Update `README.md` Quickstart to:
  - `python scripts/bootstrap.py`
  - `python prometheus.py launch`
- Separate README into `README.md` (user) and `CONTRIBUTING.md` (developer) sections, or add clear headers.

### 3. Seed Knowledge Database (P0)
**Files:** `core/bootstrap.py`, `knowledge/engine.py` or new `knowledge/seed.py`

- Add `seed_knowledge(db: Session)` function that inserts ~100 engineering facts on first boot when the knowledge graph is empty.
- Categories: USB, firmware, hardware, engineering workflows.
- Facts should be queryable via `GET /knowledge?subject=...` immediately after boot.
- Gate on `KnowledgeNode.count == 0` so it only runs once per database.

### 4. Merge Devices + Hardware (P1)
**Files:** `web/src/apps/DevicesApp.ts`, `web/src/apps/HardwareApp.ts`, `web/src/apps/App.ts`, `web/src/os/Desktop.ts`

- Remove `hardware` from `DOCK_KEYS` and `APPS`.
- Enhance `DevicesApp.ts` to include:
  - Device list (from `api.devices()`)
  - HAL interfaces/capabilities (from `api.hardware()`)
  - Telemetry panel (battery, temp, USB, BT)
  - Firmware summary
  - Recovery button
  - Event log
- This makes Devices the single pane for all physical-device interaction.

### 5. Terminal Mode Badge (P1)
**Files:** `web/src/terminal/Terminal.ts`

- Add a mode indicator in the terminal toolbar:
  - `[DESKTOP PTY]` when `sdk.kernel.isNative()` is true (real PTY)
  - `[CLI MODE]` when running in browser (simulated, Prometheus commands only)
- Update the placeholder text to match:
  - Desktop: "Native shell — type shell commands"
  - Browser: "Prometheus commands — type `help` for shortcuts"

### 6. Command Error Messages (P1)
**Files:** `core/commands.py`, `backend/main.py`

- Every command path in `dispatch_command` must return a human-readable string, never raise.
- Add a catch-all at the end of `dispatch_command` that logs the exception and returns `"error: <message>"`.
- Ensure `/commands` endpoint returns `{"response": "..."}` with the error string, never a 500.

### 7. Guided First-Launch Flow (P2)
**Files:** `web/src/os/Onboarding.ts`, `web/src/os/Desktop.ts`

- Extend `Onboarding.ts` steps:
  1. Welcome (existing)
  2. Choose AI Provider (new — only if no provider configured)
  3. Connect Demo Device (new — calls `api.devicesSimulated("esp32_01")`)
  4. Run First Simulation (new — calls `api.simulation.run("esp32_01", "disconnect")`)
  5. Keyboard shortcuts (existing)
  6. You're all set (existing)
- Skip AI step if user chose "Continue without AI".
- Mark onboarded in `localStorage` after completion.

### 8. Demo Project (P2)
**Files:** `workspace/` structure, `web/src/apps/FilesApp.ts`

- Create `workspace/Demo/` with:
  - `README.md` describing the demo board
  - `firmware/` with a stub firmware file
  - `simulation/` with a saved scenario JSON
  - `agents/` with a demo agent config
- Update `FilesApp.ts` to show `Demo/` populated on first launch when `workspace/` is empty.

### 9. README Restructure (P2)
**Files:** `README.md`

- Keep `README.md` user-focused:
  - What is Prometheus (1 sentence)
  - Quickstart (bootstrap + launch)
  - First-run guide (AI setup, demo device, simulation)
  - Link to `CONTRIBUTING.md` for developers
- Move developer docs to `CONTRIBUTING.md`:
  - Architecture
  - Testing
  - Build instructions
  - Roadmap

## Validation
- Fresh SQLite DB + `python prometheus.py launch` → assistant shows provider picker, not error.
- `python scripts/bootstrap.py` on clean machine → venv + deps + built frontend.
- First boot → knowledge search returns seeded facts.
- Devices app → connect demo device + run recovery without opening Hardware.
- Terminal shows `[DESKTOP PTY]` or `[CLI MODE]` badge.
- All `dispatch_command` paths return strings, never raise.
- Onboarding covers AI → demo device → simulation.
- `workspace/Demo/` exists with content.

## Out of Scope
- Rust PTY terminal implementation (existing simulated mode is fine for RC2)
- HAL expansion
- New Rust/Go distributed features
- Tauri installer changes
