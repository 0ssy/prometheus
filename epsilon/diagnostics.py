from __future__ import annotations

from typing import Any

from hardware.session import DeviceSession
from hardware.drivers.base import HardwareDriver
from hardware.diagnostics import HardwareDiagnostics
from core.logger import get_logger

logger = get_logger(__name__)


class EpsilonDiagnostics:
    """Epsilon hardware diagnostics engine.

    Bridges the lower-level HardwareDiagnostics into the Prometheus Core
    event stream and knowledge graph.
    """

    def __init__(self, event_bus=None, knowledge_engine=None) -> None:
        self._hardware_diagnostics = HardwareDiagnostics()
        self._event_bus = event_bus
        self._knowledge_engine = knowledge_engine

    def assess(self, device_snapshot: dict) -> dict[str, Any]:
        battery = device_snapshot.get("battery_health", 1.0)
        storage = device_snapshot.get("storage_health", 1.0)
        thermal = device_snapshot.get("thermal_state", "normal")
        connectivity = device_snapshot.get("connectivity", "online")
        overall = "ok"
        if battery < 0.4 or storage < 0.4 or thermal == "hot" or connectivity != "online":
            overall = "degraded"
        return {
            "battery": battery,
            "storage": storage,
            "thermal_state": thermal,
            "connectivity": connectivity,
            "overall": overall,
        }

    def full_report(self, session: DeviceSession) -> dict[str, Any]:
        report = self._hardware_diagnostics.full_report(session)
        if self._event_bus is not None:
            try:
                from hardware.events import DeviceConnectedEvent
                self._event_bus.publish(
                    DeviceConnectedEvent(device_id=session.device_id, transport=session.transport)
                )
            except Exception:
                pass
        return report

    def driver_report(self, driver: HardwareDriver) -> dict[str, Any]:
        """Run diagnostics against a live driver instance."""
        report = self._hardware_diagnostics.driver_diagnostics(driver)
        transport_probe = self._hardware_diagnostics.transport_probe(driver)
        report["transport_probe"] = transport_probe
        return report
