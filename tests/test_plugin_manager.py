import time

import pytest
from plugins.manager import PluginManager
from api.plugin_api import PluginApi
from api.events import PluginRanEvent, PluginErrorEvent
from core.event_bus import InMemoryEventBus


class FakePlugin:
    name = "fake_plugin"
    version = "1.0.0"
    required_contract_version = "1.0.0"

    def on_load(self) -> None:
        pass

    def run(self, context: dict) -> dict:
        return {"ok": True}


class CrashPlugin(FakePlugin):
    name = "crash_plugin"

    def run(self, context: dict) -> dict:
        raise RuntimeError("boom")


class SlowPlugin(FakePlugin):
    name = "slow_plugin"

    def run(self, context: dict) -> dict:
        time.sleep(10)
        return {"ok": True}


class TestPluginManager:
    def test_is_plugin_api(self):
        manager = PluginManager()
        assert isinstance(manager, PluginApi)

    def test_register_and_get(self):
        manager = PluginManager()
        plugin = FakePlugin()
        manager.register(plugin)
        assert manager.get("fake_plugin") is plugin

    def test_register_duplicate_warns(self):
        manager = PluginManager()
        plugin = FakePlugin()
        manager.register(plugin)
        manager.register(plugin)

    def test_list_plugins(self):
        manager = PluginManager()
        plugin = FakePlugin()
        manager.register(plugin)
        plugins = manager.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]["name"] == "fake_plugin"
        assert plugins[0]["version"] == "1.0.0"

    def test_run(self):
        manager = PluginManager()
        plugin = FakePlugin()
        manager.register(plugin)
        result = manager.run("fake_plugin", {})
        assert result == {"ok": True}

    def test_run_missing_plugin_raises(self):
        manager = PluginManager()
        with pytest.raises(ValueError, match="No such plugin"):
            manager.run("missing_plugin", {})

    def test_run_publishes_event(self):
        bus = InMemoryEventBus()
        events: list[PluginRanEvent] = []
        bus.subscribe("plugin.ran", lambda event: events.append(event))
        manager = PluginManager(event_bus=bus)
        plugin = FakePlugin()
        manager.register(plugin)

        manager.run("fake_plugin", {})

        assert len(events) == 1
        assert events[0].plugin_name == "fake_plugin"

    def test_register_incompatible_contract_version_raises(self):
        class IncompatiblePlugin(FakePlugin):
            name = "incompatible_plugin"
            required_contract_version = "2.0.0"

        manager = PluginManager()
        with pytest.raises(RuntimeError, match="Incompatible contract version"):
            manager.register(IncompatiblePlugin())

    def test_run_isolates_plugin_exception(self):
        manager = PluginManager()
        manager.register(CrashPlugin())
        result = manager.run("crash_plugin", {})
        assert "error" in result
        assert "boom" in result["error"]

    def test_run_publishes_error_event_on_crash(self):
        bus = InMemoryEventBus()
        events: list[PluginErrorEvent] = []
        bus.subscribe("plugin.error", lambda event: events.append(event))
        manager = PluginManager(event_bus=bus)
        manager.register(CrashPlugin())

        manager.run("crash_plugin", {})

        assert len(events) == 1
        assert events[0].plugin_name == "crash_plugin"
        assert "boom" in events[0].error

    def test_run_timeout_aborts_hung_plugin(self):
        manager = PluginManager()
        manager.register(SlowPlugin())
        start = time.monotonic()
        result = manager.run("slow_plugin", {}, timeout=0.5)
        elapsed = time.monotonic() - start
        assert "error" in result
        assert result["error"] == "timeout"
        assert elapsed < 5
