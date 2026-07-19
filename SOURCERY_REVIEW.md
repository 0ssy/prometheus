# Sourcery Code Review — PR #10 (feature/aether)
**Total: 27 issues (21 security, 6 other)**

---

## SECURITY ISSUES (21)

### 1. `prometheus_cli/launch.py` — Command Injection
**Severity:** HIGH
- `subprocess.Popen` called without static string — `self.cmd` could be influenced by external input
- If command data is controllable by a malicious actor, this is an instance of command injection
- **Fix:** Validate/whitelist command arguments, use `shlex.quote()` for dynamic parts, ensure `self.cmd` is constructed from trusted constants

### 2-21. `web/src/apps/DevicesApp.ts` — XSS via innerHTML (20 instances)
**Severity:** HIGH

Dynamic user-controlled data is injected into `innerHTML` assignments without sanitization:

| Location | Variable | Data Source | Count |
|----------|----------|-------------|-------|
| content.innerHTML | device_id, error messages | API response | 4 |
| devRoot.innerHTML | device_id, online status | API response | 3 |
| capRoot.innerHTML | interface name, type, connected status | API response | 2 |
| fwRoot.innerHTML | firmware format, sha256, error messages | API response | 3 |
| telemRoot.innerHTML | battery, temp, usb, bluetooth values | API response | 2 |
| outRoot.innerHTML | recovery step names, error messages | API response | 3 |
| logsRoot.innerHTML | event type, message, created_at | API response | 2 |

**Fix:** Replace `innerHTML` assignments with safe DOM manipulation:
- Use `textContent` for plain text values
- Use `createElement` + `appendChild` for structured content
- Sanitize any HTML-like data before insertion

---

## OTHER ISSUES (6)

### 1. `backend/main.py` — NameError on provider endpoints
**File:** `backend/main.py` lines 1435-1441
**Severity:** HIGH

The assistant provider endpoints call `add_provider` and `remove_provider`, but only `load_providers` and `save_providers` are imported from `core.provider_config`. This will raise a `NameError` on first request.

```python
# Current (broken):
from core.provider_config import load_providers, save_providers
providers = add_provider(provider)  # NameError!
providers = remove_provider(provider_id)  # NameError!

# Fix:
from core.provider_config import load_providers, save_providers, add_provider, remove_provider
```

### 2. `web/src/apps/DevicesApp.ts` — Device selection broken
**File:** `web/src/apps/DevicesApp.ts` lines 67-70
**Severity:** MEDIUM

The click handler derives the clicked device index but calls `load()` without using it, so the detail view always shows `devices[0]`.

```typescript
// Current (broken):
row.addEventListener("click", () => {
  const idx = parseInt((row as HTMLElement).dataset.idx || "0", 10);
  const d = devices[idx];
  if (d) load();  // always loads devices[0]
});

// Fix: thread selected index into load
row.addEventListener("click", () => {
  const idx = parseInt((row as HTMLElement).dataset.idx || "0", 10);
  const d = devices[idx];
  if (d) load(d.device_id);  // pass selected device
});
```

### 3. `scripts/bootstrap.py` — --db argument unused
**File:** `scripts/bootstrap.py` lines 65-66
**Severity:** MEDIUM

`--db` is parsed into `args.db` but never used; `boot`/`SessionLocal` still use the default DB. This is misleading for operators expecting `--db` to control the seeded database.

```python
# Current (misleading):
ap.add_argument("--db", default="./data/prometheus.db", help="SQLite database path")
args = ap.parse_args()
# ... args.db is never referenced

# Fix option A: wire it through
boot(heartbeat_job, db_path=args.db)

# Fix option B: remove the arg if not needed
```

### 4. `core/provider_config.py` — No de-duplication in add_provider
**File:** `core/provider_config.py` lines 35-39
**Severity:** MEDIUM

`add_provider` always appends without checking for an existing provider with the same `id`, leading to duplicate entries.

```python
# Current:
def add_provider(provider: dict) -> list[dict]:
    providers = load_providers()
    providers.append(provider)  # always appends
    save_providers(providers)
    return providers

# Fix: upsert by id
def add_provider(provider: dict) -> list[dict]:
    providers = load_providers()
    existing = [i for i, p in enumerate(providers) if p.get("id") == provider.get("id")]
    if existing:
        providers[existing[0]] = provider
    else:
        providers.append(provider)
    save_providers(providers)
    return providers
```

### 5. `tests/test_agents.py` — Hard-coded proposal IDs
**File:** `tests/test_agents.py` lines 68-69
**Severity:** LOW

Tests depend on the literal ID `"prop-0001"`, which will break if ID generation changes.

```python
# Current (brittle):
v1 = engine.vote("prop-0001", "agent-a", VoteChoice.APPROVE, 0.9, "looks good")
v2 = engine.vote("prop-0001", "agent-b", VoteChoice.REJECT, 0.8, "needs work")

# Fix: capture proposal_id from propose()
proposed = engine.propose(...)
v1 = engine.vote(proposed.proposal_id, "agent-a", VoteChoice.APPROVE, 0.9, "looks good")
v2 = engine.vote(proposed.proposal_id, "agent-b", VoteChoice.REJECT, 0.8, "needs work")
```

### 6. `prometheus_cli/launch.py` — Early return skips subsystems
**File:** `prometheus_cli/launch.py` lines 141-143
**Severity:** MEDIUM

Returning early when Go is missing stops the rest of the plan from being built. `prometheus launch --all` on a machine without Go will never add frontend/cloud components.

```python
# Current (broken):
if args.distributed or args.all:
    if not _check_go_available():
        print("[launch] Go toolchain not found; skipping distributed components")
        return plan  # BUG: skips everything else!

# Fix: log and continue
distributed_requested = args.distributed or args.all
if distributed_requested and not _check_go_available():
    print("[launch] Go toolchain not found; skipping distributed components")
    distributed_requested = False
# continue building plan for other subsystems...
```

---

## SUMMARY

| Category | Count | Severity |
|----------|-------|----------|
| XSS (innerHTML) | 20 | HIGH |
| Command injection | 1 | HIGH |
| NameError / bug risk | 3 | HIGH/MEDIUM |
| Misleading CLI args | 1 | MEDIUM |
| Data integrity | 1 | MEDIUM |
| Test brittleness | 1 | LOW |

**Full review:** https://github.com/0ssy/prometheus/pull/10
