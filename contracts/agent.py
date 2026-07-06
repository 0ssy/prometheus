from abc import ABC, abstractmethod
from typing import Any


class AgentApi(ABC):
    @abstractmethod
    def register(self, agent: Any) -> None: ...

    @abstractmethod
    def list_agents(self) -> list[str]: ...

    @abstractmethod
    def dispatch(
        self, agent_name: str, task: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]: ...
