from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class FirmwareDashboard:
    def list_firmware(self) -> list[dict[str, Any]]:
        return []

    def get_firmware_details(self, firmware_id: str) -> dict[str, Any]:
        return {"firmware_id": firmware_id, "details": {}}

    def get_compatibility_matrix(self) -> dict[str, Any]:
        return {"entries": []}
