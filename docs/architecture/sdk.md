# SDK Architecture

## Overview

The Prometheus SDK provides interfaces and runtimes for extending the platform at
every layer: plugins, drivers, and external integrations. It spans Python
(backend), TypeScript (frontend), and Rust (driver HAL).

## Versioning

The SDK follows semantic versioning. Each module version is declared in its
manifest:

| Module | Current Version | Compatibility |
|--------|-----------------|---------------|
| Plugin SDK | 1.0.0 | Backward-compatible within major |
| Driver SDK | 1.0.0 | Backward-compatible within major |
| Extension SDK | 1.0.0 | Backward-compatible within major |
| TypeScript SDK | 1.0.0 | Matches Plugin/Driver manifest contracts |

A plugin or driver declares its target engine versions. The runtime rejects
loads when the declared engine minimum is not satisfied.

## Plugin SDK

### Python

Plugins inherit from `plugins.base.Plugin` and are auto-discovered from
`plugins/installed/`. The plugin manager registers, validates permissions, and
executes plugins in-process.

```python
from plugins.base import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"
    version = "0.1.0"

    def run(self, context: dict) -> dict:
        return {"result": "ok"}
```

The context dict always contains `db` (SQLAlchemy session) and `logger`
(structured logger). Additional keys are merged from the API payload.

### TypeScript

The TypeScript plugin runtime (`web/src/sdk/plugin-runtime.ts`) mirrors the
Python lifecycle:

- **Loading**: Parse a manifest, validate required fields, and register.
- **Permission checking**: `execute()` rejects if required permissions are not
  granted.
- **Execution**: Proxy to the backend API with timeout and abort support.
- **Lifecycle events**: Subscribe to state transitions (`loading`, `ready`,
  `running`, `error`, `shutdown`).
- **Hot-reload**: Coordinate with `PluginHotReload` to preserve state across
  file changes.

```typescript
import { pluginRuntime } from "../sdk/plugin-runtime";

await pluginRuntime.loadManifest(manifest);
const result = await pluginRuntime.execute("my-plugin", {
  grantedPermissions: ["read"],
  simulate: false,
});
pluginRuntime.onStateChange("ready", (e) => console.log(e));
```

## Driver SDK

### Rust HAL Core

Drivers implement HAL traits defined in `hal-core`. Each trait declares methods
and a `safety_level`:

```rust
pub trait HalTrait {
    fn name(&self) -> &'static str;
    fn methods(&self) -> &[HalMethod];
    fn safety_level(&self) -> SafetyLevel;
}
```

Safety levels:
- `safe` — read-only or low-risk operations.
- `unsafe` — write operations requiring explicit approval.
- `critical` — operations requiring ownership declaration and admin review.

### TypeScript

The TypeScript driver runtime (`web/src/sdk/driver-runtime.ts`) provides:

- **Manifest loading**: Load driver manifests with HAL traits and safety policies.
- **Connection management**: Connect/disconnect devices by transport.
- **Read/Write**: Perform I/O through the backend API with safety enforcement.
- **Health**: Query driver and device health status.

```typescript
import { driverRuntime } from "../sdk/driver-runtime";

await driverRuntime.loadManifest(driverManifest);
await driverRuntime.connect("my-driver", "device-1", "USB");
const { data } = await driverRuntime.read("device-1", { length: 256 });
await driverRuntime.write("device-1", { data: new Uint8Array([0x01, 0x02]) });
```

## Extension SDK (Python)

Extensions are Python packages that add new capabilities to the engineering
modules. They use the same capability registration pattern as plugins but are
scoped to a discipline:

```python
from extensions.base import Extension

class MyExtension(Extension):
    module = "networking"
    workflows = ["capture_packets", "analyze_topology"]

    def execute(self, workflow: str, payload: dict) -> dict:
        ...
```

## Developer Tooling

### prometheus CLI

The `prometheus` CLI is the primary entry point for SDK development:

```bash
# Validate manifests
prometheus validate plugins/installed/my-plugin/manifest.json

# Run a plugin in isolation
prometheus plugin run my-plugin --simulate

# Watch a plugin directory and hot-reload on change
prometheus plugin watch my-plugin ./plugins/installed/my-plugin
```

### Package Signing

All published packages are signed. Verification happens at load time:

1. Compute SHA-256 of the package archive.
2. Verify signature against the Prometheus code-signing key.
3. Reject if the signature is missing or invalid.

### SDK Versioning Matrix

| Frontend SDK | Backend Plugin SDK | Backend Driver SDK | Notes |
|--------------|-------------------|-------------------|-------|
| 1.0.x | 1.0.x | 1.0.x | Initial release |
| 1.x | 1.x | 1.x | Minor updates are backward-compatible |
| 2.x | 2.x | 2.x | Breaking changes require manifest bump |
