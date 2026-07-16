from __future__ import annotations

from typing import Any

from contracts.device import DeviceApi
from contracts.event_bus import EventBus
from devices.registry import DeviceRegistry
from core.logger import get_logger

logger = get_logger(__name__)


class DeviceRegistryAdapter(DeviceApi):
    """Adapter wrapping the legacy DeviceRegistry for hardware/ consumers.

    Delegates all operations to the legacy ``device_registry`` singleton
    so that existing ``PlatformService`` and test code continues to work
    while the migration to ``hardware/`` proceeds.
    """

    def __init__(self, registry: DeviceRegistry | None = None, event_bus: EventBus | None = None) -> None:
        self._registry = registry or DeviceRegistry(event_bus=event_bus)

    def register(self, device: Any) -> None:
        self._registry.register(device)

    def unregister(self, device_id: str) -> None:
        self._registry.unregister(device_id)

    def get(self, device_id: str) -> Any | None:
        return self._registry.get(device_id)

    def list(self) -> list[dict]:
        return self._registry.list()
