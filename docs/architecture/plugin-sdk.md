# Plugin SDK

## Overview

Plugins extend Prometheus without modifying core code. They run inside
the same process and receive a context dict on each invocation.

## Plugin Interface

```python
from plugins.base import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"
    version = "0.1.0"

    def run(self, context: dict) -> dict:
        # Do work
        return {"result": "ok"}
```

## Registration

Plugins are auto-discovered from `plugins/installed/` or manually registered:

```python
from plugins.manager import plugin_manager
from plugins.installed.my_plugin import MyPlugin

plugin_manager.register(MyPlugin())
```

## Context Dict

The context dict passed to `run()` always contains:

| Key | Type | Description |
|-----|------|-------------|
| `db` | `Session` | SQLAlchemy database session |
| `logger` | `Logger` | Structured logger instance |

Additional keys are merged from the API request payload.

## Return Value

Plugins must return a JSON-serializable dict. Exceptions are caught by
the plugin manager and logged.

## Best Practices

- Keep plugins single-purpose.
- Do not import transport-specific libraries directly — use `devices.base.Device`.
- Record significant events as knowledge-graph facts via `assert_fact()`.
- Never write to disks or flash firmware from a plugin (use Gamma modules).
