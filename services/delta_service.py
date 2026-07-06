from __future__ import annotations

from delta.lab import DigitalEngineeringLab
from delta.scenario_engine import ScenarioEngine
from delta.time_engine import TimeEngine
from digital_twin.twin import build_twin


class DeltaService:
    def __init__(self, knowledge_engine=None, device_api=None, session_factory=None):
        self._lab = DigitalEngineeringLab()
        self._scenario_engine = ScenarioEngine()
        self._time_engine = TimeEngine()
        self._knowledge_engine = knowledge_engine
        self._device_api = device_api
        self._session_factory = session_factory

    def create_workspace(self, workspace_id: str, device_count: int) -> dict:
        return self._lab.create_workspace(workspace_id, device_count=device_count)

    def inject_failure(self, workspace_id: str, failure_type: str) -> dict:
        return self._lab.inject_failure(workspace_id, failure_type=failure_type)

    def run_scenario(self, workspace_id: str, steps: list[str]) -> dict:
        workspace = self._lab.get_workspace(workspace_id)
        result = self._scenario_engine.run(workspace, steps=steps)
        if self._knowledge_engine is not None and self._session_factory is not None:
            with self._session_scope() as db:
                self._knowledge_engine.learn(
                    db=db,
                    scenario_key=f"scenario:{workspace_id}",
                    outcome=result.get("outcome_prediction", {}).get("recovery_success_rate", "unknown"),
                    confidence=result.get("confidence_report", {}).get("confidence", 0.5),
                    context={"steps": steps},
                )
        return result

    def forecast_battery(
        self, current_health: float, months: int, monthly_degradation: float
    ) -> dict:
        return self._time_engine.forecast_battery_health(
            current_health=current_health,
            months=months,
            monthly_degradation=monthly_degradation,
        )

    def build_twin(self, device_id: str) -> dict:
        if self._device_api is None or self._session_factory is None:
            raise RuntimeError("DeltaService requires device_api and session_factory to build twins")
        with self._session_scope() as db:
            twin = build_twin(db, device_id, device_api=self._device_api)
            return twin.to_dict()

    class _SessionScope:
        def __init__(self, session_factory):
            self._session_factory = session_factory
            self._session = None

        def __enter__(self):
            self._session = self._session_factory()
            return self._session

        def __exit__(self, exc_type, exc, tb):
            if self._session is not None:
                self._session.close()

    def _session_scope(self):
        if self._session_factory is None:
            raise RuntimeError("DeltaService requires session_factory for knowledge operations")
        return DeltaService._SessionScope(self._session_factory)
