from __future__ import annotations

from typing import Any

from hardware.session import DeviceSession
from hardware.recovery import HardwareRecovery
from core.logger import get_logger

logger = get_logger(__name__)


class EpsilonRecoveryPlanner:
    """Epsilon recovery planning engine.

    Generates recovery plans but never executes them. Execution remains a
    separate, explicitly authorized step.
    """

    def __init__(self, event_bus=None, knowledge_engine=None) -> None:
        self._hardware_recovery = HardwareRecovery()
        self._event_bus = event_bus
        self._knowledge_engine = knowledge_engine

    def plan(
        self,
        device_id: str,
        risk: str,
        ownership_declared: bool,
        session: DeviceSession | None = None,
        diagnostics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not ownership_declared:
            raise RuntimeError(
                f"{device_id} is not ownership-declared. Recovery planning is blocked."
            )

        if session is not None and diagnostics is not None:
            plan = self._hardware_recovery.plan_recovery(session, diagnostics)
        else:
            if risk == "high":
                options = [
                    "Run diagnostics capability",
                    "Backup critical state",
                    "Execute recover capability",
                    "Verify device health and data integrity",
                ]
            else:
                options = [
                    "Continue monitoring",
                    "Run periodic diagnostics",
                    "Prepare rollback snapshot",
                ]
            plan = {"device_id": device_id, "risk": risk, "strategies": options}

        if self._event_bus is not None:
            try:
                from hardware.events import DeviceConnectedEvent
                self._event_bus.publish(
                    DeviceConnectedEvent(device_id=device_id, transport="recovery")
                )
            except Exception:
                pass

        return plan
