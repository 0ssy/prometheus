from unittest.mock import patch

from core.container import ServiceContainer
from main import run_platform


@patch("main.boot")
def test_run_platform_bootstraps_container(mock_boot):
    container = ServiceContainer()
    mock_boot.return_value = container

    result = run_platform()

    assert result is container
    assert mock_boot.call_count == 1
    heartbeat = mock_boot.call_args[0][0]
    assert callable(heartbeat)
