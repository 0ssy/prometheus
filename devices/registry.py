"""
Prometheus Device Registry (RFC 0001)
-----------------------------------------
In-memory dict of device_id -> Device, mirroring the plugin/agent
manager pattern on purpose — same shape, different concern. No
persistence yet: if Prometheus restarts, devices must reconnect.
That's fine for v0.1 — don't add persistence before something
actually needs devices to survive a restart.
"""
from .base import Device
from core.logger import get_logger

logger = get_logger(__name__)


class DeviceRegistry:
    def __init__(self):
        self._devices: dict[str, Device] = {}

    def register(self, device: Device) -> None:
        self._devices[device.device_id] = device
        logger.info(
            f"Registered device: {device.device_id} "
            f"(transport={device.transport}, ownership_declared={device.ownership_declared})"
        )

    def unregister(self, device_id: str) -> None:
        device = self._devices.pop(device_id, None)
        if device:
            logger.info(f"Unregistered device: {device_id}")

    def get(self, device_id: str) -> Device | None:
        return self._devices.get(device_id)

    def list(self) -> list[dict]:
        return [
            {
                "device_id": d.device_id,
                "transport": d.transport,
                "ownership_declared": d.ownership_declared,
                **d.status(),
            }
            for d in self._devices.values()
        ]


device_registry = DeviceRegistry()