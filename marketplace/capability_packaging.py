from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class CapabilityPackager:
    def package_capability(
        self,
        capability_name: str,
        version: str,
        executor_path: str,
    ) -> dict[str, Any]:
        return {
            "name": capability_name,
            "version": version,
            "format": "prometheus-cap",
            "status": "stub",
        }

    def verify_package(self, package_data: bytes) -> dict[str, Any]:
        return {"valid": False, "status": "stub"}

    def install_package(self, package_data: bytes) -> dict[str, Any]:
        return {"installed": False, "status": "stub"}
