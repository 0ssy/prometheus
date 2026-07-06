from __future__ import annotations

from typing import Any


class ScenarioEngine:
    def run(self, workspace: dict[str, Any], steps: list[str]) -> dict[str, Any]:
        risk_score = 0.0
        for step in steps:
            if step in {"boot_loop", "partition_corruption", "battery_failure"}:
                risk_score += 0.3
            elif step in {"usb_failure", "factory_reset"}:
                risk_score += 0.2
            else:
                risk_score += 0.1
        risk_score = min(1.0, risk_score)
        success_rate = max(0.0, 1.0 - risk_score)
        confidence = max(0.5, 1.0 - (risk_score / 2.0))
        return {
            "workspace_id": workspace["workspace_id"],
            "steps": steps,
            "outcome_prediction": {
                "recovery_success_rate": success_rate,
                "risk_score": risk_score,
            },
            "confidence_report": {"confidence": confidence},
        }
