from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class DiagnosticsDashboard:
    def list_diagnostics(self) -> list[dict[str, Any]]:
        logger.debug("Listing diagnostics")
        return []

    def get_diagnostic_report(self, device_id: str) -> dict[str, Any]:
        logger.debug("Fetching diagnostic report for %s", device_id)
        return {
            "device_id": device_id,
            "found": False,
            "issues": [],
        }
