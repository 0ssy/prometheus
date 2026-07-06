import pytest
from plugins.manager import PluginManager
from api.plugin_api import PluginApi


class FakePlugin:
    name = "fake_plugin"
    version = "1.0.0"

    def on_load(self) -> None:
        pass

    def run(self, context: dict) -> dict:
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
