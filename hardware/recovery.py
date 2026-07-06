from __future__ import annotations

from typing import Any

from hardware.session import DeviceSession
from hardware.diagnostics import HardwareDiagnostics
from core.logger import get_logger

logger = get_logger(__name__)


class HardwareRecovery:
    """Provides recovery planning for hardware devices.

    This class returns recovery strategies and does not execute them.
    """

    def assess_risk(self, session: DeviceSession, diagnostics: dict[str, Any]) -> str:
        """Assess the risk level of a device based on diagnostics.

        Args:
            session: The device session to assess.
            diagnostics: Diagnostic data for the session.

        Returns:
            A risk level string: 'low', 'medium', or 'high'.
        """
        overall = diagnostics.get("overall_status", "ok")
        if overall != "ok":
            return "high"
        battery = diagnostics.get("battery", {}).get("battery_health", 1.0)
        storage = diagnostics.get("storage", {}).get("health", "healthy")
        if battery < 0.3 or storage != "healthy":
            return "medium"
        return "low"

    def plan_recovery(
        self, session: DeviceSession, diagnostics: dict[str, Any], digital_twin: Any | None = None
    ) -> dict[str, Any]:
        """Plan a recovery strategy for a device.

        Args:
            session: The device session to plan recovery for.
            diagnostics: Diagnostic data for the session.
            digital_twin: Optional digital twin for simulation.

        Returns:
            A recovery plan dictionary.
        """
        risk = self.assess_risk(session, diagnostics)
        if risk == "low":
            strategies = ["Continue monitoring", "Prepare rollback snapshot"]
        elif risk == "medium":
            strategies = [
                "Run diagnostics capability",
                "Backup critical state",
                "Execute recover capability",
                "Verify device health and data integrity",
            ]
        else:
            strategies = [
                "Run diagnostics capability",
                "Backup critical state",
                "Execute recover capability",
                "Verify device health and data integrity",
                "Factory reset (last resort)",
            ]
        logger.info(f"Planned recovery for {session.device_id}: risk={risk}")
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "risk": risk,
            "strategies": strategies,
            "requires_approval": risk in ("medium", "high"),
            "digital_twin_simulated": digital_twin is not None,
        }

    def recommend(self, device_id: str, risk_level: str) -> list[dict[str, Any]]:
        """Recommend recovery options for a device.

        Args:
            device_id: The device identifier.
            risk_level: The assessed risk level.

        Returns:
            A list of recommended recovery options.
        """
        options = [
            {
                "action": "monitor",
                "description": "Continue monitoring device state.",
            },
            {
                "action": "backup",
                "description": "Backup critical device state before recovery.",
            },
            {
                "action": "recover",
                "description": "Execute the recover capability.",
            },
        ]
        if risk_level in ("medium", "high"):
            options.append(
                {
                    "action": "reset",
                    "description": "Perform a full device reset if recovery fails.",
                }
            )
        return options
