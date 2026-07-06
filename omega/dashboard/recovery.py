from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class RecoveryDashboard:
    def list_recovery_plans(self) -> list[dict[str, Any]]:
        return []

    def get_recovery_plan(self, plan_id: str) -> dict[str, Any]:
        return {"plan_id": plan_id, "plan": {}}
