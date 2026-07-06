from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class AgentsDashboard:
    def list_agents(self) -> list[dict[str, Any]]:
        return []

    def get_agent_details(self, agent_name: str) -> dict[str, Any]:
        return {"agent": agent_name, "details": {}}

    def get_agent_tasks(self, agent_name: str) -> list[dict[str, Any]]:
        return []
