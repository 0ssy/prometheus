from __future__ import annotations

from dataclasses import dataclass, field
import threading

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentPackage:
    name: str
    version: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    author: str = ""
    checksum: str = ""


class AgentRepository:
    def __init__(self) -> None:
        self._agents: dict[str, AgentPackage] = {}
        self._lock = threading.RLock()

    def register(self, agent: AgentPackage) -> str:
        agent_id = f"{agent.name}@{agent.version}"
        with self._lock:
            self._agents[agent_id] = agent
            logger.info("Registered agent: %s", agent_id)
        return agent_id

    def discover(self, capability: str | None = None) -> list[AgentPackage]:
        with self._lock:
            results = list(self._agents.values())
            if capability:
                results = [a for a in results if capability in a.capabilities]
            return results

    def get(self, name: str) -> AgentPackage | None:
        with self._lock:
            for agent in self._agents.values():
                if agent.name == name:
                    return agent
            return None

    def list_available(self) -> list[AgentPackage]:
        with self._lock:
            return list(self._agents.values())
