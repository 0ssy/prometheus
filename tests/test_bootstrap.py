from unittest.mock import patch
from core.bootstrap import boot
from core.container import ServiceContainer


class TestBootstrap:
    @patch("core.bootstrap.init_db")
    def test_boot_returns_container(self, mock_init_db):
        container = boot(lambda: None)
        assert isinstance(container, ServiceContainer)
        container.get("scheduler").stop()

    @patch("core.bootstrap.init_db")
    def test_boot_registers_services(self, mock_init_db):
        container = boot(lambda: None)
        assert container.get("config") is not None
        assert container.get("db_engine") is not None
        assert container.get("memory_api") is not None
        assert container.get("reasoning_api") is not None
        assert container.get("plugin_api") is not None
        assert container.get("agent_api") is not None
        assert container.get("device_api") is not None
        assert container.get("platform_service") is not None
        assert container.get("event_handlers") is not None
        assert container.get("scheduler") is not None
        container.get("scheduler").stop()

    @patch("core.bootstrap.init_db")
    def test_boot_loads_plugins(self, mock_init_db):
        container = boot(lambda: None)
        plugin_api = container.get("plugin_api")
        plugins = plugin_api.list_plugins()
        assert any(p["name"] == "echo" for p in plugins)
        container.get("scheduler").stop()

    @patch("core.bootstrap.init_db")
    def test_boot_loads_agents(self, mock_init_db):
        container = boot(lambda: None)
        agent_api = container.get("agent_api")
        agents = agent_api.list_agents()
        assert "echo_agent" in agents
        assert "engineering_agent" in agents
        scheduler = container.get("scheduler")
        assert "heartbeat" in scheduler.list_jobs()
        scheduler.stop()
