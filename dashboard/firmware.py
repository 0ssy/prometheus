from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class FirmwareDashboard:
    def list_firmware(self) -> list[dict[str, Any]]:
        logger.debug("Listing firmware")
        return []

    def get_firmware_details(self, firmware_id: str) -> dict[str, Any]:
        logger.debug("Fetching firmware details for %s", firmware_id)
        return {
            "firmware_id": firmware_id,
            "found": False,
        }

    def get_compatibility_matrix(self) -> dict[str, Any]:
        logger.debug("Computing firmware compatibility matrix")
        return {
            "devices": {},
            "firmware_versions": [],
        }
