# Prometheus Post-Review Hardening & "Real Assistant" Plan

## Context

A reviewer **ran the software** (`python prometheus.py`) and flagged a gap between
what Prometheus *claims* to be and what it *demonstrably does*. The user's synthesis
agrees with most conclusions and sets three priorities. This plan closes the
**Critical** and **Medium** items and implements the user's chosen Assistant
architecture (decided below). It is scoped to the v1.0 / RC1 hardening cycle and does
**not** touch the Aether Rust roadmap beyond aligning the shared provider contract.

### Locked decisions (from user)
1. **Assistant architecture — Option 1, Aether-as-specification:**
   - `python prometheus.py` (standalone) → **Python LLM client** → OpenAI-compatible API.
   - Tauri Desktop → **Rust Aether** (`aether_ask`) → OpenAI-compatible API.
   - Both share the **same provider config + same protocol** (OpenAI-compatible), but are
     independent. Python must **never** depend on the desktop/Rust process existing.
   - Aether = provider abstraction + context + tools + permissions + orchestration.
     The transport to the model is secondary.
2. **Split the endpoint:** `/assistant` = LLM-backed conversational assistant;
   `/commands` (new) = deterministic command execution (the old router). No more
   silent echo pretending to be an AI.
3. **Web UI Assistant panel targets `/assistant`** (Python LLM) so it works in BOTH
   deployment modes. `aether_ask` (Rust) is the richer desktop-native path, deferred
   to Phase 3 (out of scope here).

## Decisions on contested points (user overrides reviewer)
- **Not a "skeleton" / not "just CRUD":** keep all existing capability/plugin/kernel/
  simulation/digital-twin code. No removals of functionality. The fix is *presentation &
  data hygiene*, not architecture rewrite.
- **Version:** collapse to ONE canonical version constant (see Task A1). Recommend value
  `1.0.0-rc1` to match the tagged release; confirm against the actual tag before bump.

---

## Task list (ordered)

### A. Critical — must fix before v1.0

**A1. Single source of truth for version** (`core/config.py`)
- `config.version` is canonical. Set it to the release value (recommend `1.0.0-rc1`).
- `omega/dashboard/dashboard_hub.py:33` (`version="0.5.0-epsilon"`) → `config.version`.
- `dashboard/overview.py:45` (`version="0.9.0"`) → `config.version`.
- `backend/main.py` `/health` (`:110`) and `/version` (`:1308`) already use `config.version` — keep.
- `web/` SPA: stop hardcoding a version; render it from `GET /version` (or Vite env seeded
  from one place). Ensure `web/package.json` version matches or is derived.
- Validation: `curl /health`, `curl /version`, `curl /omega/dashboard/overview` all report
  the same string.

**A2. Fresh clone must be fresh** — stop shipping runtime data
- `git rm --cached data/prometheus.db data/prometheus.log` (keep local files; they'll be
  regenerated on first boot — dirs are already `os.makedirs(..., exist_ok=True)` in
  `core/database.py:24` and `core/logger.py:33`).
- `git rm data/prometheus.db.corrupted.20260711133604` — a junk leftover from a prior run;
  delete entirely.
- `.gitignore`: add explicit `data/prometheus.db`, `data/prometheus.log`,
  `data/prometheus.db.corrupted.*` (the existing `*.db`/`*.log` entries don't cover the
  tracked files; untracking + explicit patterns is required).

**A3. Clean git tree after `python prometheus.py`** — covered by A2's gitignore. Confirm no
other runtime artifact lands in a tracked path (logs/db/corrupt-backups all under ignored
`data/`). Add a CI assertion: run the server briefly, then `git status --porcelain` is empty.

**A4. Make the Assistant real + rename the router** (`backend/main.py`, new `services/llm_client.py`)
- New `services/llm_client.py`:
  - `LLMClient` with `chat(system: str, user: str) -> str` and `is_configured() -> bool`.
  - POSTs OpenAI-shaped JSON to `{llm_base_url}/chat/completions`, parses
    `choices[0].message.content`. Use `httpx` (add to `requirements.txt` only if absent).
  - `list_models()` optional (GET `{llm_base_url}/models`).
- `core/config.py`: add `llm_base_url` (default `http://localhost:1234/v1`), `llm_model`
  (default `local-model`), `llm_api_key` (default `""`). Env-overridable
  (`PROMETHEUS_LLM_BASE_URL`, etc.).
- Rewrite `POST /assistant` (`main.py:1261`):
  - If `not llm_client.is_configured()`: return
    `{"response": "No language model configured. Set PROMETHEUS_LLM_* or run with an OpenAI-compatible provider (e.g. LM Studio)."}`
  - Else: build a system prompt ("Prometheus — engineering intelligence OS…"), call
    `llm_client.chat`, return `{"response": content}`.
  - **Remove** the old command-router branches from `/assistant`.
- New `POST /commands` = the old router logic (dispatch/show devices/show agents/show
  kernel/status/help), now honestly labeled as a command console.

**A5. Demos/tests must not pollute production data**
- `prometheus.py run_demo()` (`prometheus.py:222`) writes to the real `data/prometheus.db`
  (`store_memory`, device, knowledge graph, twin). Fix: run the demo against an ephemeral
  DB — bind its `SessionLocal` to `sqlite:///:memory:` or a `tempfile` and pass that
  session in. Do not touch `config.db_path`.
- Add a `--db PATH` override to the `demo` subcommand for repeatable ephemeral runs.
- Existing unit tests already use `:memory:`/`tmp_path` — keep; add a guard test that
  running the demo leaves `data/prometheus.db` unmodified.

### B. Medium priority

**B1. README — one launch path up top**
- `README.md` Quickstart = exactly: `git clone` → `pip install -r requirements.txt` →
  `python prometheus.py` → `curl /health`.
- Move Tauri desktop build, SDK install, `npm`/frontend build, advanced config under a
  clear **"Advanced"** section. Update the `Olympus (in progress)` title to reflect RC1.

**B2. Empty placeholder folders**
- Remove the empty `.gitkeep` placeholder dirs: `labs/ai`, `labs/firmware`, `labs/quantum`,
  `labs/recovery`, `labs/robotics`, `labs/vision`, `labs/voice`, and `graveyard/`.
- Keep `labs/README.md` but rewrite it as a **roadmap** describing planned lab areas
  (so intent is preserved without implying shipped code).

**B3. One command grammar (unify terminal + console + SDK)**
- New `core/commands.py` (or extend `services/platform_service.py`): a single
  `dispatch_command(raw: str) -> str` mapping user-facing verbs to the **capability
  registry** (`core/capabilities.py`, `contracts/capability.py`).
- Canonical verbs: `connect device`, `run simulation`, `open knowledge`, `list agents`,
  `search firmware`, `dispatch <agent> <task>`, `status`, `help`.
- Refactor `prometheus.py --terminal` (`_terminal_command`, `prometheus.py:434`) and the
  new `/commands` handler to both call `dispatch_command`. SDK already speaks capabilities
  — align terminology; no new SDK surface needed.
- Validation: same input string issued from terminal and from `/commands` yields identical
  behavior/result.

### C. Aether spec alignment (Phase 1 now; Phase 2/3 noted)

- **Phase 1 (this cycle):** `services/llm_client.py` + `core/config.py` LLM settings +
  `/assistant` LLM-backed + clear no-model message. `python prometheus.py` stays fully
  standalone. The shared contract = OpenAI-compatible chat completions.
- **Phase 2 (next):** Aether (Rust, M1 done) keeps the same provider list, config format,
  and model selection. Document the shared provider-config schema (env vars / future
  `providers.json`) so Python and Rust agree.
- **Phase 3 (later, OUT of scope):** context engine, tool calling, memory, workspace
  awareness, permissions move into Aether; desktop Assistant may prefer `aether_ask`.

---

## Validation

- `cd crates/ai-runtime && cargo test` (existing Aether M1 tests stay green).
- `pytest` (Python): all existing 225+ tests green; add tests for `llm_client`
  (mock `/v1/chat/completions`), `/assistant` no-model message, `/commands` parity, and
  demo-non-pollution.
- `git status --porcelain` is empty after `python prometheus.py` (A3).
- Fresh clone: `git clone` → no `data/prometheus.db`/`.log` present; first `python
  prometheus.py` creates them.
- Version parity: `/health` == `/version` == `/omega/dashboard/overview` == web footer.
- Manual (needs LM Studio): `python prometheus.py`, POST `/assistant` with a real question
  returns model text; POST `/commands` with `help` returns the command list.

## Risks / open questions
- **LLM dep:** confirm `httpx` is in `requirements.txt`; if not, add it (runtime, not test-only).
- **Conversation state:** Phase 1 `/assistant` is single-turn. Multi-turn history is Phase 3
  (Aether context engine). Acceptable for RC1.
- **Canonical version value:** confirm `1.0.0-rc1` vs `1.0.0` against the actual git tag
  before bumping.
- **Web UI scope:** Assistant + Command Console panels + version-from-API are the only
  `web/` changes this cycle; no broader React rework.

## Out of scope (explicitly deferred)
- Aether Rust context engine / tool calling / permissions / memory (Phase 3).
- Routing the Python backend *through* the Rust process (rejected — breaks standalone mode).
- PostgreSQL migration, new SDK surface, full desktop UI rework beyond the Assistant/Console.
- Any Python capability/plugin/kernel logic removal.
