import pytest

from simulation.engine import SimulationEngine


def test_simulation_engine_generates_report():
    engine = SimulationEngine()
    result = engine.simulate(
        device_id="dev-a",
        device_state={"connected": True},
        failure_mode="disconnect",
    )

    assert result["virtual_device_id"] == "virtual::dev-a"
    assert result["risk"] == "high"
    assert result["verification"]["passed"] is True


def test_simulation_engine_rejects_unknown_failure_mode():
    engine = SimulationEngine()
    with pytest.raises(ValueError, match="failure_mode must be one of"):
        engine.simulate("dev-a", {"connected": True}, "unknown")
