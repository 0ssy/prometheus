"""
Prometheus Agent Manager
-----------------------------------------
Registry + dispatcher for agents, mirroring the plugin manager's
shape on purpose — same pattern, different concern. Plugins extend
capability; agents perform tasks using that capability.
"""

from .base import PrometheusAgent
from contracts.agent import AgentApi
from contracts.event_bus import EventBus
from api.events import AgentDispatchedEvent, AgentStatusChangedEvent
from core.logger import get_logger
from core.event_bus import event_bus as default_event_bus

logger = get_logger(__name__)


class AgentManager(AgentApi):
    def __init__(self, event_bus: EventBus | None = None):
        self._agents: dict[str, PrometheusAgent] = {}
        self._status: dict[str, str] = {}
        self._last_task: dict[str, dict] = {}
        self._updated_at: dict[str, str] = {}
        self._event_bus = event_bus or default_event_bus

    def register(self, agent: PrometheusAgent) -> None:
        self._agents[agent.name] = agent
        self._status[agent.name] = "connected"
        self._updated_at[agent.name] = utc_now_iso()
        logger.info(f"Registered agent: {agent.name}")

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    def get_agent_status(self, agent_name: str) -> dict:
        return {
            "name": agent_name,
            "status": self._status.get(agent_name, "unknown"),
            "last_task": self._last_task.get(agent_name),
            "updated_at": self._updated_at.get(agent_name),
        }

    def list_agent_statuses(self) -> list[dict]:
        return [self.get_agent_status(name) for name in self._agents.keys()]

    def _set_status(self, agent_name: str, status: str, task: dict | None = None) -> None:
        self._status[agent_name] = status
        self._updated_at[agent_name] = utc_now_iso()
        if task is not None:
            self._last_task[agent_name] = task
        self._event_bus.publish(
            AgentStatusChangedEvent(agent_name=agent_name, status=status, last_task=task)
        )

    def dispatch(self, agent_name: str, task: dict, context: dict) -> dict:
        agent = self._agents.get(agent_name)
        if agent is None:
            raise ValueError(f"No such agent: {agent_name}")
        self._set_status(agent_name, "running", task)
        logger.info(f"Dispatching task to agent '{agent_name}': {task}")
        try:
            result = agent.perform(task, context)
            self._event_bus.publish(AgentDispatchedEvent(agent_name=agent_name, task=task))
            self._set_status(agent_name, "idle", task)
            return result
        except Exception as e:
            self._set_status(agent_name, "error", task)
            raise


def utc_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


agent_manager = AgentManager()
