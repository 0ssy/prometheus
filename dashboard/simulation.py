from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class SimulationDashboard:
    def list_simulations(self) -> list[dict[str, Any]]:
        logger.debug("Listing simulations")
        return []

    def get_simulation_results(self, simulation_id: str) -> dict[str, Any]:
        logger.debug("Fetching results for simulation %s", simulation_id)
        return {
            "simulation_id": simulation_id,
            "found": False,
        }

    def get_simulation_stats(self) -> dict[str, Any]:
        logger.debug("Computing simulation stats")
        return {
            "total_simulations": 0,
            "completed": 0,
            "running": 0,
            "failed": 0,
        }
