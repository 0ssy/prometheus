from services.delta_service import DeltaService


def test_delta_service_workspace_and_scenario():
    delta = DeltaService()
    workspace = delta.create_workspace("ws1", device_count=3)
    assert workspace["workspace_id"] == "ws1"
    assert len(workspace["virtual_devices"]) == 3

    degraded = delta.inject_failure("ws1", "network")
    assert degraded["virtual_networks"][0]["status"] == "degraded"

    scenario = delta.run_scenario("ws1", ["boot_loop", "usb_failure"])
    assert scenario["workspace_id"] == "ws1"
    assert "confidence_report" in scenario


def test_delta_service_time_forecast():
    delta = DeltaService()
    forecast = delta.forecast_battery(1.0, months=12, monthly_degradation=0.02)
    assert forecast["projected_health"] == 0.76
