from __future__ import annotations

from contracts.device import DeviceApi
from core.logger import get_logger
from delta.scenario_engine import ScenarioEngine
from delta.time_engine import TimeEngine
from delta.lab import DigitalEngineeringLab
from digital_twin.twin import build_twin
from hardware.session import DeviceSession, DeviceSessionManager
from hardware.drivers.virtual import VirtualDriver
from hardware.events import (
    DeviceConnectedEvent,
    DeviceDisconnectedEvent,
    DeviceUnresponsiveEvent,
    BatteryLowEvent,
    FirmwareDetectedEvent,
    DriverFailedEvent,
    SessionExpiredEvent,
)
from security.authorization import Authorizer, AuthorizationResult
from security.permissions import default_registry
from security.auditing import AuditLogger
from security.integrity import IntegrityVerifier
from epsilon.hal import EpsilonHAL
from epsilon.diagnostics import EpsilonDiagnostics
from epsilon.recovery import EpsilonRecoveryPlanner
from epsilon.firmware import EpsilonFirmwareIntelligence

logger = get_logger(__name__)


class EpsilonService:
    def __init__(
        self,
        device_api: DeviceApi,
        delta_service=None,
        session_factory=None,
        event_bus=None,
        knowledge_engine=None,
    ):
        self._device_api = device_api
        self._hal = EpsilonHAL()
        self._session_manager = DeviceSessionManager()
        self._diagnostics = EpsilonDiagnostics(event_bus=event_bus, knowledge_engine=knowledge_engine)
        self._recovery = EpsilonRecoveryPlanner(event_bus=event_bus, knowledge_engine=knowledge_engine)
        self._firmware = EpsilonFirmwareIntelligence()
        self._authorizer = Authorizer(registry=default_registry)
        self._audit = AuditLogger()
        self._integrity = IntegrityVerifier()
        self._delta_service = delta_service
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._knowledge_engine = knowledge_engine

    def list_interfaces(self) -> dict:
        return {"interfaces": self._hal.list_interfaces()}

    def register_default_interfaces(self) -> dict:
        self._hal._register_default_drivers()
        return {"interfaces": self._hal.list_interfaces()}

    def connect_device(self, device_id: str, driver_name: str = "virtual", actor: str = "system", permissions: set[str] | None = None) -> dict:
        permissions = permissions or set()
        auth = self._authorizer.authorize(actor, "device.connect", device_id, permissions)
        if not auth.allowed:
            self._audit.record(actor, "device.connect", device_id, "denied", {"reason": auth.reason})
            raise RuntimeError(f"Authorization denied: {auth.reason}")

        driver_cls = self._hal.get_interface(driver_name)
        driver = driver_cls(name=device_id)
        result = driver.connect()
        session = self._session_manager.create_session(
            device_id=device_id,
            driver_name=driver_name,
            transport=driver.transport,
        )
        if self._event_bus is not None:
            self._event_bus.publish(DeviceConnectedEvent(device_id=device_id, transport=driver.transport))
        self._audit.record(actor, "device.connect", device_id, "allowed", {"session_id": session.session_id})
        return {"device_id": device_id, "session_id": session.session_id, "result": result}

    def disconnect_device(self, device_id: str, actor: str = "system", permissions: set[str] | None = None) -> dict:
        permissions = permissions or set()
        auth = self._authorizer.authorize(actor, "device.disconnect", device_id, permissions)
        if not auth.allowed:
            self._audit.record(actor, "device.disconnect", device_id, "denied", {"reason": auth.reason})
            raise RuntimeError(f"Authorization denied: {auth.reason}")

        sessions = [s for s in self._session_manager.list_sessions() if s.device_id == device_id]
        for session in sessions:
            self._session_manager.close_session(session.session_id)
            if self._event_bus is not None:
                self._event_bus.publish(DeviceDisconnectedEvent(device_id=device_id, reason="user_request"))
        self._audit.record(actor, "device.disconnect", device_id, "allowed")
        return {"device_id": device_id, "disconnected": len(sessions) > 0}

    def diagnostics(self, device_id: str) -> dict:
        device = self._device_api.get(device_id)
        if device is None:
            raise RuntimeError(f"No such device: {device_id}")
        status = device.status()
        snapshot = {
            "battery_health": status.get("battery_health", 1.0),
            "storage_health": status.get("storage_health", 1.0),
            "thermal_state": status.get("thermal_state", "normal"),
            "connectivity": "online" if status.get("connected", True) else "offline",
        }
        result = self._diagnostics.assess(snapshot)
        if self._delta_service is not None and self._session_factory is not None:
            try:
                self._delta_service.build_twin(device_id)
            except Exception:
                pass
        return result

    def firmware_summary(self, metadata: dict) -> dict:
        return self._firmware.summarize(metadata)

    def recovery_plan(self, device_id: str, risk: str = "high") -> dict:
        device = self._device_api.get(device_id)
        if device is None:
            raise RuntimeError(f"No such device: {device_id}")
        plan = self._recovery.plan(
            device_id=device_id,
            risk=risk,
            ownership_declared=bool(device.ownership_declared),
        )
        if self._delta_service is not None and self._session_factory is not None:
            try:
                twin = self._delta_service.build_twin(device_id)
                plan["digital_twin"] = twin
            except Exception:
                pass
        return plan

    def full_diagnostics(self, device_id: str) -> dict:
        device = self._device_api.get(device_id)
        if device is None:
            raise RuntimeError(f"No such device: {device_id}")
        sessions = [s for s in self._session_manager.list_sessions() if s.device_id == device_id]
        if not sessions:
            return {"error": "no active session", "device_id": device_id}
        session = sessions[0]
        report = self._diagnostics.full_report(session)
        return report

    def firmware_parse(self, data: bytes) -> dict[str, Any]:
        return self._firmware.parse(data)
