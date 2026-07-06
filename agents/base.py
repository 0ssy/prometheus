"""
Prometheus Agent — Base Contract
-----------------------------------------
An agent is a named, runnable unit with its own memory tag. Phase
Alpha agents are simple synchronous task-runners. Multi-agent
coordination, message-passing between agents, and autonomous
scheduling loops are Phase Epsilon territory — don't reach for
that complexity yet.
"""
from abc import ABC, abstractmethod
from typing import Any


class PrometheusAgent(ABC):
    name: str = "unnamed_agent"

    @abstractmethod
    def perform(self, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a task. context contains {"db": Session, "logger": Logger}.
        Must return a JSON-serializable result dict.
        """
        ...
