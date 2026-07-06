from happy_path import run_happy_path


def test_happy_path_end_to_end_report():
    report = run_happy_path()
    assert report["status"] == "ok"
    assert any(plugin["name"] == "echo" for plugin in report["plugins_loaded"])
    assert "echo_agent" in report["agents_loaded"]
    assert report["devices_registered"] >= 1
    assert "scheduler" in report["services_registered"]
