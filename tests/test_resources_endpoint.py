from unittest.mock import MagicMock

from backend.main import system_resources


def test_system_resources_returns_dict():
    mock_container = MagicMock()
    mock_rm = MagicMock()
    mock_rm.to_dict.return_value = {
        "cpu_percent": 10.0,
        "memory_mb": 1024.0,
        "disk_mb": 5000.0,
        "network_mbps": 0.0,
        "active_connections": 5,
        "limits": {},
        "throttled": False,
        "throttle_reason": None,
    }
    mock_container.get.return_value = mock_rm
    result = system_resources(container=mock_container)
    assert result["cpu_percent"] == 10.0
    assert result["memory_mb"] == 1024.0

