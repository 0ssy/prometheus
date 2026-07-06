"""
Prometheus Agent Manager
-----------------------------------------
Registry + dispatcher for agents, mirroring the plugin manager's
shape on purpose — same pattern, different concern. Plugins extend
capability; agents perform tasks using that capability.
"""

from .base import PrometheusAgent
from api.agent_api import AgentApi
from api.events import AgentDispatchedEvent
from core.logger import get_logger
from core.event_bus import event_bus

logger = get_logger(__name__)


class AgentManager(AgentApi):
    def __init__(self):
        self._agents: dict[str, PrometheusAgent] = {}

    def register(self, agent: PrometheusAgent) -> None:
        self._agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    def dispatch(self, agent_name: str, task: dict, context: dict) -> dict:
        agent = self._agents.get(agent_name)
        if agent is None:
            raise ValueError(f"No such agent: {agent_name}")
        logger.info(f"Dispatching task to agent '{agent_name}': {task}")
        result = agent.perform(task, context)
        event_bus.publish(AgentDispatchedEvent(agent_name=agent_name, task=task))
        return result


agent_manager = AgentManager()
