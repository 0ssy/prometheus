"""
Prometheus Plugin SDK — Public package surface.

Exposes the plugin authoring framework for Phase Omega (Olympus):
interfaces, decorators, lifecycle management, and a testing harness.
"""

from .interfaces import (
    BasePlugin,
    PluginCapability,
    PluginContext,
    PluginManifest,
    PluginResult,
)
from .decorators import (
    capability,
    plugin,
    plugin_hook,
    requires_permission,
)
from .lifecycle import (
    PluginLifecycle,
    PluginLifecycleError,
    PluginLifecycleManager,
    PluginState,
)
from .testing import (
    MockPluginContext,
    PluginTestHarness,
    PluginTestSuite,
    TestResult,
)

__all__ = [
    "BasePlugin",
    "PluginCapability",
    "PluginContext",
    "PluginManifest",
    "PluginResult",
    "capability",
    "plugin",
    "plugin_hook",
    "requires_permission",
    "PluginLifecycle",
    "PluginLifecycleError",
    "PluginLifecycleManager",
    "PluginState",
    "MockPluginContext",
    "PluginTestHarness",
    "PluginTestSuite",
    "TestResult",
]
