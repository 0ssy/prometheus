"""
Echo Agent — Reference Implementation
-----------------------------------------
Proves the agent contract works and demonstrates writing to the
knowledge graph. A "device tracking" task here stands in for what
will eventually be the Digital Twin Engine (Phase Delta).
"""

from .base import PrometheusAgent
from reasoning.graph import assert_fact


class EchoAgent(PrometheusAgent):
    name = "echo_agent"

    def perform(self, task: dict, context: dict) -> dict:
        db = context["db"]
        device_id = task.get("device_id", "device_unknown")
        status = task.get("status", "seen")

        assert_fact(db, subject=device_id, predicate="status", obj=status)

        return {"agent": self.name, "device_id": device_id, "recorded_status": status}
