from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class SimulationDashboard:
    def list_simulations(self) -> list[dict[str, Any]]:
        return []

    def get_simulation_results(self, simulation_id: str) -> dict[str, Any]:
        return {"simulation_id": simulation_id, "results": {}}

    def get_simulation_stats(self) -> dict[str, Any]:
        return {"total": 0, "passed": 0, "failed": 0}
