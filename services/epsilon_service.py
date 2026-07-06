from __future__ import annotations

from contracts.device import DeviceApi
from epsilon.diagnostics import DiagnosticsEngine
from epsilon.firmware import FirmwareKnowledge
from epsilon.hal import HALRegistry
from epsilon.recovery import RecoveryPlanner


class EpsilonService:
    def __init__(self, device_api: DeviceApi):
        self._device_api = device_api
        self._hal = HALRegistry()
        self._diagnostics = DiagnosticsEngine()
        self._recovery = RecoveryPlanner()
        self._firmware = FirmwareKnowledge()

    def register_default_interfaces(self) -> dict:
        self._hal.register_default_interfaces()
        return {"interfaces": self._hal.list_interfaces()}

    def list_interfaces(self) -> dict:
        return {"interfaces": self._hal.list_interfaces()}

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
        return self._diagnostics.assess(snapshot)

    def firmware_summary(self, metadata: dict) -> dict:
        return self._firmware.summarize(metadata)

    def recovery_plan(self, device_id: str, risk: str = "high") -> dict:
        device = self._device_api.get(device_id)
        if device is None:
            raise RuntimeError(f"No such device: {device_id}")
        return self._recovery.plan(
            device_id=device_id,
            risk=risk,
            ownership_declared=bool(device.ownership_declared),
        )
