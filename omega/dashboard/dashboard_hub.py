from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from core.config import config
from core.logger import get_logger

logger = get_logger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


class OverviewDashboard:
    def get_overview(self) -> PlatformOverview:
        return PlatformOverview(
            platform_name="Prometheus",
            version=config.version,
            uptime_seconds=0.0,
            status="ok",
            total_devices=0,
            active_sessions=0,
            total_capabilities=0,
            total_plugins=0,
            total_agents=0,
        )

    def get_health_status(self) -> dict[str, Any]:
        return {"status": "ok", "components": {}}

    def get_summary(self) -> dict[str, Any]:
        overview = self.get_overview()
        return {
            "platform": overview.platform_name,
            "version": overview.version,
            "status": overview.status,
            "devices": overview.total_devices,
            "sessions": overview.active_sessions,
            "capabilities": overview.total_capabilities,
            "plugins": overview.total_plugins,
            "agents": overview.total_agents,
        }


class DashboardHub:
    def __init__(self) -> None:
        self._overview = OverviewDashboard()
        self._sections: dict[str, Any] = {
            "overview": self._overview,
        }

    def register_section(self, name: str, dashboard: Any) -> None:
        self._sections[name] = dashboard

    def get_dashboard(self, section: str = "overview") -> dict[str, Any]:
        dashboard = self._sections.get(section, self._overview)
        if hasattr(dashboard, "get_summary"):
            return dashboard.get_summary()
        if hasattr(dashboard, "get_overview"):
            return dashboard.get_overview()
        return {}

    def list_sections(self) -> list[str]:
        return list(self._sections.keys())
