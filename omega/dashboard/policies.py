from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class PoliciesDashboard:
    def list_policies(self) -> list[dict[str, Any]]:
        return []

    def list_permissions(self) -> list[dict[str, Any]]:
        return []

    def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        return []
