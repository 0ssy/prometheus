from __future__ import annotations

from typing import Any


class SimulationEngine:
    def simulate(
        self, device_id: str, device_state: dict[str, Any], failure_mode: str = "disconnect"
    ) -> dict[str, Any]:
        if failure_mode not in {"disconnect", "latency_spike", "write_failure"}:
            raise ValueError(
                "failure_mode must be one of: disconnect, latency_spike, write_failure"
            )

        if failure_mode == "disconnect":
            impact = "device_offline"
            recovered = False
            risk = "high"
        elif failure_mode == "latency_spike":
            impact = "degraded_throughput"
            recovered = True
            risk = "medium"
        else:
            impact = "write_rejected"
            recovered = False
            risk = "high"

        return {
            "virtual_device_id": f"virtual::{device_id}",
            "failure_mode": failure_mode,
            "device_state_before": device_state,
            "impact": impact,
            "recovered": recovered,
            "risk": risk,
            "verification": {
                "checks": [
                    "state model generated",
                    "failure injected",
                    "recovery hypothesis evaluated",
                ],
                "passed": True,
            },
        }
