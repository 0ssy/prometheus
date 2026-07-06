from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import threading
import uuid

from core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class AgentPackage:
    name: str
    version: str
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    author: str = ""
    checksum: str = ""


class AgentRepository:
    def __init__(self) -> None:
        self._agents: dict[str, AgentPackage] = {}
        self._lock = threading.RLock()
        self._logger = get_logger(__name__)

    def register(self, agent: AgentPackage) -> str:
        with self._lock:
            aid = str(uuid.uuid4())
            self._agents[aid] = agent
            self._logger.info(
                f"Registered agent: {agent.name} v{agent.version}"
            )
            return aid

    def discover(self, capability: str | None = None) -> list[AgentPackage]:
        with self._lock:
            results = list(self._agents.values())
            if capability:
                results = [a for a in results if capability in a.capabilities]
            return results

    def get(self, name: str) -> AgentPackage | None:
        with self._lock:
            for agt in self._agents.values():
                if agt.name == name:
                    return agt
            return None

    def list_available(self) -> list[AgentPackage]:
        with self._lock:
            return list(self._agents.values())
