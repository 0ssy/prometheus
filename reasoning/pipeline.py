from __future__ import annotations

from typing import Any


class ReasoningPipeline:
    def evaluate(self, simulation_result: dict[str, Any], device_id: str) -> dict[str, Any]:
        observation = {
            "failure_mode": simulation_result["failure_mode"],
            "impact": simulation_result["impact"],
            "risk": simulation_result["risk"],
            "recovered": simulation_result["recovered"],
        }

        if observation["risk"] == "high":
            hypothesis = "System may become unavailable without intervention."
            plan_steps = [
                "Isolate failing path",
                "Attempt recovery capability",
                "Re-check simulated health",
            ]
            recommended_capability = f"device.{device_id}.recover"
            should_execute = False
        else:
            hypothesis = "System remains operational with degraded performance."
            plan_steps = [
                "Continue monitoring",
                "Run diagnostics capability",
                "Collect additional telemetry",
            ]
            recommended_capability = f"device.{device_id}.diagnose"
            should_execute = False

        verification = {
            "criteria": ["risk assessed", "plan generated", "capability selected"],
            "passed": True,
        }
        recommendation = {
            "recommended_capability": recommended_capability,
            "execute_now": should_execute,
            "reason": hypothesis,
        }
        return {
            "observation": observation,
            "hypothesis": hypothesis,
            "plan": {"steps": plan_steps},
            "verification": verification,
            "recommendation": recommendation,
        }
