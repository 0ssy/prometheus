from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_demo_with_custom_db_does_not_touch_default(tmp_path):
    prod_db = Path("data/prometheus.db")
    if not prod_db.exists():
        prod_db.parent.mkdir(parents=True, exist_ok=True)
        prod_db.write_bytes(b"x")
    original_size = prod_db.stat().st_size

    mock_platform = MagicMock()
    mock_platform.run_plugin.return_value = "ok"
    mock_platform.dispatch_agent.return_value = "ok"
    mock_platform.register_simulated_device.return_value = {"device_id": "demo", "transport": "sim"}
    mock_platform.store_memory.return_value = MagicMock(id="m1")
    mock_platform.get_facts.return_value = []
    mock_twin = MagicMock(state="active", health="ok")
    mock_platform.dispatch_agent.return_value = "ok"

    mock_container = MagicMock()
    mock_container.resolve.return_value = mock_platform
    mock_container.list_services.return_value = ["svc"]
    mock_container.get.side_effect = lambda key: {
        "scheduler": MagicMock(stop=MagicMock()),
        "plugin_api": MagicMock(list_plugins=MagicMock(return_value=["echo"])),
        "agent_api": MagicMock(list_agents=MagicMock(return_value=["echo_agent"])),
        "device_api": MagicMock(list=MagicMock(return_value=[])),
    }.get(key, MagicMock())

    with patch("prometheus.boot", return_value=mock_container):
        with patch("prometheus.SessionLocal") as mock_session_cls:
            mock_db = MagicMock()
            mock_db.query.return_value.scalar.return_value = 0
            mock_session_cls.return_value.__enter__.return_value = mock_db
            mock_session_cls.return_value.__exit__.return_value = False
            with patch("prometheus._run_plugin"):
                with patch("prometheus._run_agent"):
                    with patch("prometheus._create_device"):
                        with patch("prometheus._store_memory"):
                            with patch("prometheus._query_knowledge_graph"):
                                with patch("prometheus._build_twin", return_value=mock_twin):
                                    with patch("prometheus._generate_report", return_value={"platform": "test"}):
                                        from prometheus import run_demo
                                        report = run_demo(db_path=str(tmp_path / "demo.db"))

    assert report["db_path"] == str(tmp_path / "demo.db")
    if prod_db.exists():
        assert prod_db.stat().st_size == original_size
