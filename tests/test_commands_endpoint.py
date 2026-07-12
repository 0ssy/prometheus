from unittest.mock import MagicMock, patch

import pytest

from backend.main import commands_endpoint


def _make_container(mock_platform=None, mock_agent_api=None, mock_plugin_api=None, mock_kernel=None, mock_sim_engine=None, mock_device_api=None, mock_capability_api=None, mock_hardware_hal=None):
    mock_container = MagicMock()
    if mock_platform is not None:
        mock_container.resolve.return_value = mock_platform
    mapping = {
        "agent_api": mock_agent_api or MagicMock(),
        "plugin_api": mock_plugin_api or MagicMock(),
        "kernel": mock_kernel or MagicMock(),
        "simulation_engine": mock_sim_engine or MagicMock(),
        "device_api": mock_device_api or MagicMock(),
        "capability_api": mock_capability_api or MagicMock(),
        "hardware_hal": mock_hardware_hal or MagicMock(),
    }
    mock_container.get.side_effect = lambda key: mapping.get(key, MagicMock())
    return mock_container


def test_commands_help():
    result = commands_endpoint(
        payload={"command": "help"},
        db=MagicMock(),
        container=_make_container(),
    )
    assert "status" in result["response"]
    assert "connect" in result["response"]


def test_commands_status():
    mock_db = MagicMock()
    mock_db.query.return_value.scalar.return_value = 5
    with patch("core.commands._status_snapshot") as mock_snap:
        mock_snap.return_value = {"kernel": "Running", "agents": 2}
        result = commands_endpoint(
            payload={"command": "status"},
            db=mock_db,
            container=_make_container(),
        )
    assert "kernel: Running" in result["response"]
    assert "agents: 2" in result["response"]


def test_commands_connect():
    mock_platform = MagicMock()
    mock_platform.register_simulated_device.return_value = {"device_id": "dev1", "transport": "simulated"}
    result = commands_endpoint(
        payload={"command": "connect dev1"},
        db=MagicMock(),
        container=_make_container(mock_platform=mock_platform),
    )
    assert "connected dev1" in result["response"]
    mock_platform.register_simulated_device.assert_called_once_with(device_id="dev1")


def test_commands_list_agents():
    mock_agent_api = MagicMock()
    mock_agent_api.list_agents.return_value = ["agent-a", "agent-b"]
    result = commands_endpoint(
        payload={"command": "list agents"},
        db=MagicMock(),
        container=_make_container(mock_agent_api=mock_agent_api),
    )
    assert "agent-a" in result["response"]
    assert "agent-b" in result["response"]


def test_commands_show_kernel():
    mock_kernel = MagicMock()
    mock_kernel.status.return_value = {"status": "alive"}
    result = commands_endpoint(
        payload={"command": "show kernel"},
        db=MagicMock(),
        container=_make_container(mock_kernel=mock_kernel),
    )
    assert mock_kernel.status.called


def test_commands_requires_command():
    with pytest.raises(RuntimeError):
        commands_endpoint(payload={}, db=MagicMock(), container=MagicMock())
