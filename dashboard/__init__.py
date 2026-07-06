from __future__ import annotations

from typing import Any

from core.logger import get_logger

from .agents import AgentsDashboard
from .devices import DeviceDashboard
from .diagnostics import DiagnosticsDashboard
from .firmware import FirmwareDashboard
from .knowledge import KnowledgeDashboard
from .logs import LogsDashboard
from .metrics import MetricsDashboard
from .overview import OverviewDashboard, PlatformOverview
from .policies import PoliciesDashboard
from .plugins import PluginsDashboard
from .recovery import RecoveryDashboard
from .simulation import SimulationDashboard

logger = get_logger(__name__)

_SECTION_MAP: dict[str, str] = {
    "overview": "overview",
    "devices": "devices",
    "knowledge": "knowledge",
    "simulation": "simulation",
    "firmware": "firmware",
    "diagnostics": "diagnostics",
    "recovery": "recovery",
    "agents": "agents",
    "plugins": "plugins",
    "metrics": "metrics",
    "logs": "logs",
    "policies": "policies",
}


class DashboardHub:
    def __init__(self) -> None:
        self.overview = OverviewDashboard()
        self.devices = DeviceDashboard()
        self.knowledge = KnowledgeDashboard()
        self.simulation = SimulationDashboard()
        self.firmware = FirmwareDashboard()
        self.diagnostics = DiagnosticsDashboard()
        self.recovery = RecoveryDashboard()
        self.agents = AgentsDashboard()
        self.plugins = PluginsDashboard()
        self.metrics = MetricsDashboard()
        self.logs = LogsDashboard()
        self.policies = PoliciesDashboard()
        logger.info("DashboardHub initialized")

    def get_dashboard(self, section: str | None = None) -> dict[str, Any]:
        if section is None or section == "all":
            return self._full_overview()

        if section not in _SECTION_MAP:
            logger.warning("Unknown dashboard section: %s", section)
            return {"error": f"Unknown dashboard section: {section}"}

        return getattr(self, section).get_overview() if section == "overview" else self._render_section(section)

    def _render_section(self, section: str) -> dict[str, Any]:
        dashboard = getattr(self, section)
        result: dict[str, Any] = {}
        for attr in dir(dashboard):
            if attr.startswith("_") or attr == "get_overview":
                continue
            method = getattr(dashboard, attr)
            if callable(method):
                try:
                    result[attr] = method()
                except TypeError:
                    result[attr] = f"<method {attr} requires arguments>"
        return result

    def _full_overview(self) -> dict[str, Any]:
        return {
            "overview": self.overview.get_overview().to_dict(),
            "health": self.overview.get_health_status(),
            "summary": self.overview.get_summary(),
            "sections": list(_SECTION_MAP.keys()),
        }


__all__ = [
    "DashboardHub",
    "OverviewDashboard",
    "PlatformOverview",
    "DeviceDashboard",
    "KnowledgeDashboard",
    "SimulationDashboard",
    "FirmwareDashboard",
    "DiagnosticsDashboard",
    "RecoveryDashboard",
    "AgentsDashboard",
    "PluginsDashboard",
    "MetricsDashboard",
    "LogsDashboard",
    "PoliciesDashboard",
]
