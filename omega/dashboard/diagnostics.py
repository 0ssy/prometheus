from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class DiagnosticsDashboard:
    def list_diagnostics(self) -> list[dict[str, Any]]:
        return []

    def get_diagnostic_report(self, device_id: str) -> dict[str, Any]:
        return {"device_id": device_id, "report": {}}
