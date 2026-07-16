from __future__ import annotations

from sdk.plugin_sdk import (
    BasePlugin,
    PluginContext,
    PluginLifecycleManager,
    PluginManifest,
    PluginResult,
    PluginTestHarness,
    MockPluginContext,
    capability,
    plugin,
    requires_permission,
)
from sdk.plugin_sdk.examples import BatteryAnalyzer, TemperatureMonitor


def test_plugin_manifest_creation():
    manifest = PluginManifest(
        name="demo",
        version="1.2.3",
        description="a demo plugin",
        author="tester",
        capabilities=["cap_a"],
    )
    assert manifest.name == "demo"
    assert manifest.version == "1.2.3"
    assert manifest.capabilities == ["cap_a"]
    assert manifest.dependencies == []
    assert manifest.entrypoint == ""


def test_base_plugin_initialize():
    class DemoPlugin(BasePlugin):
        manifest = PluginManifest(name="demo", version="1.0.0", description="d", author="a")

    p = DemoPlugin()
    ctx = PluginContext(kernel=None, capability_manager=None, knowledge_engine=None, event_bus=None, logger=None)
    p.initialize(ctx)
    health = p.health()
    assert health["status"] == "healthy"
    assert health["plugin"] == "demo"


def test_plugin_decorator_registers_capabilities():
    @plugin
    class DemoPlugin:
        name = "decorated"
        version = "1.0.0"
        description = "d"
        author = "a"
        capabilities = []
        dependencies = []
        entrypoint = ""

        @capability
        def do_work(self) -> PluginResult:
            """Do some work."""
            return PluginResult.ok({"done": True})

    assert issubclass(DemoPlugin, BasePlugin)
    assert DemoPlugin.manifest.name == "decorated"
    assert "do_work" in DemoPlugin.manifest.capabilities
    cap_map = getattr(DemoPlugin, "__plugin_capabilities__")
    assert "do_work" in cap_map
    assert cap_map["do_work"]["description"] == "Do some work."


def test_capability_decorator():
    @capability
    def sample(self) -> int:
        """Return a number."""
        return 42

    caps = getattr(sample, "__plugin_capabilities__")
    assert caps["description"] == "Return a number."
    assert caps["permissions"] == set()

    @capability
    @requires_permission("x.read")
    def guarded(self) -> int:
        """Guarded capability."""
        return 1

    caps = getattr(guarded, "__plugin_capabilities__")
    assert caps["permissions"] == {"x.read"}


def test_plugin_lifecycle_manager():
    mgr = PluginLifecycleManager()
    plugin_obj = BatteryAnalyzer()
    state = mgr.register("battery_analyzer", plugin_obj)
    assert state.lifecycle.value == "registered"

    ctx = PluginContext(kernel=None, capability_manager=None, knowledge_engine=None, event_bus=None, logger=None)
    ctx.granted_permissions = {"battery.read"}
    mgr.set_context(ctx)
    state = mgr.initialize("battery_analyzer")
    assert state.lifecycle.value == "ready"

    result = mgr.execute("battery_analyzer", {"capability": "analyze_battery", "cell_id": "cell-1"})
    assert result.success
    assert result.data["cell_id"] == "cell-1"

    state = mgr.shutdown("battery_analyzer")
    assert state.lifecycle.value == "registered"


def test_plugin_test_harness():
    harness = PluginTestHarness(MockPluginContext(granted_permissions={"battery.read"}))
    harness.load_plugin(BatteryAnalyzer)
    result = harness.execute("analyze_battery", {"cell_id": "cell-2"})
    harness.assert_success(result)
    harness.assert_contains(result, "state_of_charge")
    assert result.data["state_of_charge"] == 0.87


def test_plugin_example_battery_analyzer():
    plugin = BatteryAnalyzer()
    ctx = PluginContext(kernel=None, capability_manager=None, knowledge_engine=None, event_bus=None, logger=None)
    ctx.granted_permissions = {"battery.read"}
    plugin.initialize(ctx)
    result = plugin.execute({"capability": "analyze_battery", "cell_id": "cell-9"})
    assert result.success
    assert result.data["health_percent"] == 94.2
    assert result.data["cycle_count"] == 412


def test_plugin_example_temperature_monitor():
    plugin = TemperatureMonitor()
    ctx = PluginContext(kernel=None, capability_manager=None, knowledge_engine=None, event_bus=None, logger=None)
    ctx.granted_permissions = {"sensor.read"}
    plugin.initialize(ctx)
    result = plugin.execute({"capability": "read_temperature", "sensor_id": "core-1"})
    assert result.success
    assert result.data["temperature_c"] == 42.3
    assert result.data["humidity_percent"] == 38.1
