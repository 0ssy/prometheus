from __future__ import annotations

from typing import Any

from hardware.session import DeviceSession
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

    def backup(self, session: DeviceSession) -> dict[str, Any]:
        """Backup device state before recovery.

        Args:
            session: The device session to backup.

        Returns:
            Backup metadata dictionary.
        """
        logger.info(f"Backup planned for {session.device_id}")
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "status": "backup_ready",
            "backup_id": f"backup-{session.session_id}",
        }

    def restore(self, session: DeviceSession, backup_data: dict[str, Any]) -> dict[str, Any]:
        """Restore device state from backup.

        Args:
            session: The device session to restore.
            backup_data: Previously captured backup metadata.

        Returns:
            Restore result dictionary.
        """
        logger.info(f"Restore planned for {session.device_id}")
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "status": "restore_ready",
            "backup_id": backup_data.get("backup_id"),
        }

    def factory_reset(self, session: DeviceSession) -> dict[str, Any]:
        """Perform factory reset on the device.

        Args:
            session: The device session to reset.

        Returns:
            Factory reset result dictionary.
        """
        logger.info(f"Factory reset planned for {session.device_id}")
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "status": "factory_reset_ready",
            "requires_approval": True,
        }
