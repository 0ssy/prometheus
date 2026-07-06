from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class AgentsDashboard:
    def list_agents(self) -> list[dict[str, Any]]:
        logger.debug("Listing agents")
        return []

    def get_agent_details(self, agent_name: str) -> dict[str, Any]:
        logger.debug("Fetching details for agent %s", agent_name)
        return {
            "agent_name": agent_name,
            "found": False,
        }

    def get_agent_tasks(self, agent_name: str) -> list[dict[str, Any]]:
        logger.debug("Fetching tasks for agent %s", agent_name)
        return []
