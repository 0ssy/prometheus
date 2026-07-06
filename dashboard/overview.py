from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PlatformOverview:
    platform_name: str
    version: str
    uptime_seconds: float
    status: str
    total_devices: int
    active_sessions: int
    total_capabilities: int
    total_plugins: int
    total_agents: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform_name": self.platform_name,
            "version": self.version,
            "uptime_seconds": self.uptime_seconds,
            "status": self.status,
            "total_devices": self.total_devices,
            "active_sessions": self.active_sessions,
            "total_capabilities": self.total_capabilities,
            "total_plugins": self.total_plugins,
            "total_agents": self.total_agents,
        }


class OverviewDashboard:
    def __init__(self) -> None:
        self._start_time: float = 0.0

    def get_overview(self) -> PlatformOverview:
        logger.debug("Computing platform overview")
        return PlatformOverview(
            platform_name="Prometheus",
            version="0.9.0",
            uptime_seconds=self._uptime_seconds(),
            status="operational",
            total_devices=0,
            active_sessions=0,
            total_capabilities=0,
            total_plugins=0,
            total_agents=0,
        )

    def get_health_status(self) -> dict[str, Any]:
        logger.debug("Computing health status")
        overview = self.get_overview()
        return {
            "status": overview.status,
            "uptime_seconds": overview.uptime_seconds,
            "components": {
                "devices": "ok",
                "knowledge": "ok",
                "simulation": "ok",
                "firmware": "ok",
                "agents": "ok",
            },
        }

    def get_summary(self) -> dict[str, Any]:
        logger.debug("Computing summary")
        overview = self.get_overview()
        return {
            "overview": overview.to_dict(),

            "health": self.get_health_status()["status"],
        }

    def _uptime_seconds(self) -> float:
        import time

        if self._start_time == 0.0:
            self._start_time = time.monotonic()
        return max(0.0, time.monotonic() - self._start_time)
