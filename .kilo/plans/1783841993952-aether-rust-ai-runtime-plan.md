# Project Aether — Rust AI Runtime (Milestone 1)

## Context

Prometheus v1.0 (RC1, tag `v1.0.0-rc1`) is frozen except for bug fixes. The
next architectural milestone is **Project Aether**: a Rust AI Runtime that
becomes the brain coordinating AI providers, built *alongside* — not inside —
the Python platform. This plan covers **Milestone 1 only**: the abstraction
layer + one local provider + a thin Tauri command surface. Later stages
(context engine, tool calling, permissions, event-driven runtime, engineering
model) are scoped out of this milestone and listed at the end.

### Grounding facts (verified in repo)
- `src-tauri` (`prometheus-src` v0.6.0, Tauri v2, edition 2021, `rust-version = 1.77.2`)
  already spawns the Python backend as a sidecar on `127.0.0.1:8000` and waits
  for it to listen (`src-tauri/src/lib.rs`). So **Rust→Python is already
  HTTP/REST over localhost** — the runtime reuses existing endpoints
  (`/capabilities`, `/knowledge`, `/memory`, `/devices`, `/agents`, `/health`)
  instead of inventing new IPC.
- No root `Cargo.toml` and no `crates/` dir exist yet. `cargo` (Rust 1.77+)
  is installed on this machine.
- `feature/ai-runtime-rust` exists (created during RC1 planning) with no
  unique commits; `feature/aether` does not exist yet.
- Python services MUST NOT be modified this milestone (RC1 freeze).

## Resolved decisions
1. **Layout:** `crates/ai-runtime` is a standalone library crate; `src-tauri/Cargo.toml`
   depends on it via `ai-runtime = { path = "../crates/ai-runtime" }`. No root
   workspace (keeps the verified RC1 `cargo tauri build` intact).
2. **Tauri depth:** add Tauri commands + Rust tests, **no React UI change**.
3. **First provider:** LM Studio (OpenAI-compatible `/v1/chat/completions` +
   `/v1/models`, default port 1234). OpenAI/OpenRouter/Gemini later reuse this
   shape.
4. **IPC:** HTTP/REST to FastAPI on `127.0.0.1:8000` (matches sidecar).

## Milestone 1 scope (build this)
```
AI Runtime (crates/ai-runtime)
├── Provider trait          (async: id/kind/health/chat/list_models)
├── Provider Registry       (in-memory map of Box<dyn Provider>)
├── Provider Manager        (register/unregister/default/set_default/list/health_all)
├── Health Checker          (aggregate provider + Prometheus /health)
├── Context Engine          (STUB: returns empty Context)
├── Tool Dispatcher         (STUB: returns "not implemented")
└── LM Studio provider      (OpenAI-compatible HTTP via reqwest)
```
Plus: 3 Tauri commands in `src-tauri/src/lib.rs` (`aether_health`,
`aether_list_providers`, `aether_ask`), Rust unit/integration tests, and a
cross-platform `aether.yml` CI job limited to the `ai-runtime` crate.

## Out of scope this milestone
Provider System beyond LM Studio; Model Manager UI (Stage 3); Context Engine
population (Stage 4); Tool Calling (Stage 5); Permissions (Stage 6);
event-driven runtime (Stage 7); engineering model (Stage 8); any Python edits;
any React UI.

## File changes
- `crates/ai-runtime/Cargo.toml` (new) — lib crate, edition 2021.
- `crates/ai-runtime/src/lib.rs` + modules (`provider.rs`, `registry.rs`,
  `manager.rs`, `health.rs`, `context.rs`, `tools.rs`, `lm_studio.rs`,
  `types.rs`, `error.rs`).
- `src-tauri/Cargo.toml` — add `ai-runtime` path dep.
- `src-tauri/src/lib.rs` — manage `AetherRuntime` state; add 3 commands.
- `.github/workflows/aether.yml` (new) — `cargo build -p ai-runtime` +
  `cargo test -p ai-runtime` on ubuntu + windows.
- Branch: create `feature/aether` from `main`; delete redundant
  `feature/ai-runtime-rust`.

## Implementation tasks (ordered)
1. **Branch:** `git checkout -b feature/aether origin/main`; `git branch -D feature/ai-runtime-rust` (local+remote) since it has no unique work.
2. **Init crate:** `crates/ai-runtime/Cargo.toml` with deps:
   `tokio` (rt-multi-thread, macros), `reqwest` (0.12, `default-features=false`,
   features `["json","rustls-tls"]` — avoids OpenSSL), `serde`/`serde_json`,
   `thiserror`. Dev: `tokio` test, `httpmock` (mock the OpenAI-compatible API).
   Edition 2021, `rust-version = "1.77"`.
3. **Core types + error (`types.rs`, `error.rs`):** `ChatMessage`
   (system/user/assistant/tool roles), `ChatRequest { model, messages,
   tools?, stream? }`, `ChatResponse { content, tool_calls?, model }`,
   `ProviderHealth { ok, latency_ms, detail }`, `ProviderKind` enum
   (LmStudio, OpenAi, Anthropic, Gemini, OpenRouter, CustomHttp — only LmStudio
   implemented now). `AetherError` (thiserror): `Http`, `Provider`, `NotFound`,
   `BackendUnreachable`, `Json`.
4. **Provider trait (`provider.rs`):** `pub trait Provider: Send + Sync`
   with `fn id(&self) -> &str`, `fn kind(&self) -> ProviderKind`,
   `async fn health(&self) -> ProviderHealth`,
   `async fn chat(&self, req: ChatRequest) -> Result<ChatResponse, AetherError>`,
   `async fn list_models(&self) -> Result<Vec<String>, AetherError>`.
5. **Registry + Manager (`registry.rs`, `manager.rs`):** `ProviderRegistry`
   holds `HashMap<String, Box<dyn Provider>>` behind interior mutability
   (`std::sync::Mutex` or `RwLock`). `ProviderManager` wraps it with
   `register`, `unregister`, `get(id)`, `list()`, `default_id()`,
   `set_default(id)`, `health_all()` (futures joined via `tokio::join!`).
   Keep a `default_id: Option<String>`; fall back to first registered.
6. **Health Checker (`health.rs`):** `check_runtime(manager, backend_url)`
   → calls each provider `health()` and `GET {backend_url}/health`; returns
   aggregated `RuntimeHealth { providers: Vec<ProviderHealth>, backend:
   ProviderHealth }`.
7. **Context Engine (`context.rs`) + Tool Dispatcher (`tools.rs`) STUBS:**
   `ContextEngine::assemble()` returns `Context::empty()` (fields reserved:
   workspace/project/files/knowledge/memory/hardware/agents/terminal — unused
   now). `ToolDispatcher::dispatch(name, args)` returns
   `Err(AetherError::Provider("tool calling not implemented in M1"))`.
   Document the Stage 4/5 contracts in doc comments.
8. **LM Studio provider (`lm_studio.rs`):** holds `base_url`
   (default `http://localhost:1234`), `name`, optional `api_key` (unused
   locally). `chat` → `POST {base_url}/v1/chat/completions` with OpenAI-shaped
   JSON (echo `model` from request; if empty, use `"local-model"`). `health` →
   `GET {base_url}/v1/models` (ok iff 2xx, measure latency). `list_models` →
   parse `/v1/models`. Register one default LM Studio provider at runtime init.
9. **Tauri integration (`src-tauri/src/lib.rs`):** define
   `struct AetherRuntime(Mutex<ProviderManager>)` (+ `ContextEngine`,
   `ToolDispatcher`); `.manage(...)` in `setup`. Commands:
   - `#[tauri::command] async fn aether_health() -> RuntimeHealth`
   - `#[tauri::command] async fn aether_list_providers() -> Vec<ProviderInfo>`
   - `#[tauri::command] async fn aether_ask(prompt: String, provider: Option<String>) -> Result<String, String>`
     builds `ChatRequest` (single user message), calls default or named
     provider `chat`, returns `content` (maps `AetherError` → `String`).
   Wire commands into `generate_handler!([..., aether_health,
   aether_list_providers, aether_ask])`.
10. **Tests (`crates/ai-runtime/src/*.rs` + `tests/`):**
    - Unit: `ChatRequest`/`ChatResponse` serde round-trip; registry
      add/remove/default/set_default; `health_all` ordering.
    - Integration (LM Studio): with `httpmock`, stand up a fake
      `/v1/chat/completions` + `/v1/models`, assert `chat` parses content and
      `health` reports ok; assert `list_models` parses names.
    - Live call test `#[tokio::test] #[ignore]` hitting real
      `localhost:1234` (skipped in CI when LM Studio absent).
11. **CI (`.github/workflows/aether.yml`):** `actions/checkout@v4`,
    `dtolnay/rust-toolchain@stable` (1.77+), `cargo build -p ai-runtime`,
    `cargo test -p ai-runtime`. Matrix ubuntu + windows. **Do NOT** build the
    full Tauri app here (needs WebView2/NSIS/webkit2gtk); keep Tauri build in
    the Windows-only `installer.yml`. Optional: `cargo fmt --check`,
    `cargo clippy -p ai-runtime -D warnings`.

## Validation plan
- `cd crates/ai-runtime && cargo test` → all unit + httpmock integration tests green.
- `cargo build -p ai-runtime` clean on stable 1.77.
- `cd src-tauri && cargo check` compiles with the new path dep + commands
  (verifies Tauri glue without a full desktop build).
- `aether.yml` green on both OS runners.
- Manual (needs a machine running LM Studio): `cargo run -p ai-runtime`
  example or a Tauri dev run calling `aether_ask("ping")` returns model text
  and `aether_health()` shows LM Studio `ok` + backend `ok`.

## Risks
- **reqwest TLS:** use `rustls-tls` (no system OpenSSL) so cross-platform CI
  builds without native libs.
- **Tauri full build in CI:** explicitly limited to `ai-runtime` crate to avoid
  WebView2/webkit2gtk/NSIS failures; the verified RC1 desktop build is untouched.
- **LM Studio absence:** live chat is `#[ignore]`; CI only runs mocked tests.
- **Provider default when none healthy:** `aether_ask` must return a clear
  `Err` ("no provider available") rather than panic.

## Open questions / later stages (not this milestone)
- Stage 3 Model Manager: persist provider config (file/SQLite), user add/remove
  UI in `web/`.
- Stage 4 Context Engine: populate from `/knowledge`, `/memory`, `/devices`,
  `/agents`, terminal history via the existing REST API.
- Stage 5 Tool Dispatcher: map tool calls → `POST /capabilities/execute` (and
  device/plugin endpoints) using `PlatformService.execute_capability`.
- Stage 6 Permissions: gate mutating tools behind explicit approval.
- Stage 7 Event-driven: subscribe to the Python event bus (SSE `/events`) instead
  of polling.
- Stage 8 Engineering model: a Prometheus-specific fine-tune/specialization.
- Whether to eventually route the Python `/assistant` endpoint through Aether
  (cross-language) or keep Aether Rust-only and let the desktop UI call the
  Tauri commands directly.
