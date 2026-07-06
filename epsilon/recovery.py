from __future__ import annotations


class RecoveryPlanner:
    def plan(self, device_id: str, risk: str, ownership_declared: bool) -> dict:
        if not ownership_declared:
            raise RuntimeError(
                f"{device_id} is not ownership-declared. Recovery planning is blocked."
            )
        if risk == "high":
            options = [
                "Run diagnostics capability",
                "Backup critical state",
                "Execute recover capability",
                "Verify device health and data integrity",
            ]
        else:
            options = [
                "Continue monitoring",
                "Run periodic diagnostics",
                "Prepare rollback snapshot",
            ]
        return {"device_id": device_id, "risk": risk, "options": options}
