from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class DeviceDashboard:
    def list_devices(self) -> list[dict[str, Any]]:
        logger.debug("Listing devices")
        return []

    def get_device_details(self, device_id: str) -> dict[str, Any]:
        logger.debug("Fetching device details for %s", device_id)
        return {
            "device_id": device_id,
            "found": False,
        }

    def get_device_health(self, device_id: str) -> dict[str, Any]:
        logger.debug("Fetching device health for %s", device_id)
        return {
            "device_id": device_id,
            "status": "unknown",
        }
