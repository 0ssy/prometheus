from __future__ import annotations

from delta.lab import DigitalEngineeringLab
from delta.scenario_engine import ScenarioEngine
from delta.time_engine import TimeEngine


class DeltaService:
    def __init__(self):
        self._lab = DigitalEngineeringLab()
        self._scenario_engine = ScenarioEngine()
        self._time_engine = TimeEngine()

    def create_workspace(self, workspace_id: str, device_count: int) -> dict:
        return self._lab.create_workspace(workspace_id, device_count=device_count)

    def inject_failure(self, workspace_id: str, failure_type: str) -> dict:
        return self._lab.inject_failure(workspace_id, failure_type=failure_type)

    def run_scenario(self, workspace_id: str, steps: list[str]) -> dict:
        workspace = self._lab.get_workspace(workspace_id)
        return self._scenario_engine.run(workspace, steps=steps)

    def forecast_battery(
        self, current_health: float, months: int, monthly_degradation: float
    ) -> dict:
        return self._time_engine.forecast_battery_health(
            current_health=current_health,
            months=months,
            monthly_degradation=monthly_degradation,
        )
