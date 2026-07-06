from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from contracts.agent import AgentApi
from contracts.device import DeviceApi
from contracts.event_bus import EventBus
from contracts.memory import MemoryApi
from contracts.plugin import PluginApi
from contracts.reasoning import ReasoningApi
from core.logger import get_logger
from api.events import DeviceConnectionFailedEvent, DeviceWriteEvent

logger = get_logger(__name__)


class PlatformService:
    def __init__(
        self,
        plugin_api: PluginApi,
        agent_api: AgentApi,
        device_api: DeviceApi,
        memory_api: MemoryApi,
        reasoning_api: ReasoningApi,
        event_bus: EventBus,
    ):
        self._plugin_api = plugin_api
        self._agent_api = agent_api
        self._device_api = device_api
        self._memory_api = memory_api
        self._reasoning_api = reasoning_api
        self._event_bus = event_bus

    def run_plugin(self, db: Session, plugin_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        context = {"db": db, "logger": logger, **payload}
        return self._plugin_api.run(plugin_name, context)

    def dispatch_agent(
        self, db: Session, agent_name: str, task: dict[str, Any]
    ) -> dict[str, Any]:
        context = {"db": db, "logger": logger}
        return self._agent_api.dispatch(agent_name, task, context)

    def store_memory(
        self, db: Session, content: str, tag: str = "general", source: str = "api"
    ) -> Any:
        return self._memory_api.remember(db, content=content, tag=tag, source=source)

    def get_memory(self, db: Session, tag: str | None = None, limit: int = 50) -> list[Any]:
        return self._memory_api.recall(db, tag=tag, limit=limit)

    def store_fact(self, db: Session, subject: str, predicate: str, obj: str) -> Any:
        return self._reasoning_api.assert_fact(db, subject, predicate, obj)

    def get_facts(
        self, db: Session, subject: str | None = None, predicate: str | None = None
    ) -> list[Any]:
        return self._reasoning_api.query_facts(db, subject=subject, predicate=predicate)

    def register_simulated_device(
        self,
        device_id: str,
        latency_seconds: float = 0.0,
        failure_rate: float = 0.0,
        ownership_declared: bool = True,
    ) -> dict[str, Any]:
        from devices.simulated import SimulatedDevice

        device = SimulatedDevice(
            device_id=device_id,
            ownership_declared=ownership_declared,
            latency_seconds=latency_seconds,
            failure_rate=failure_rate,
        )
        device.connect()
        self._device_api.register(device)
        return {"device_id": device_id, "transport": "simulated", **device.status()}

    def register_serial_device(
        self,
        device_id: str,
        port: str,
        baudrate: int = 115200,
        ownership_declared: bool = False,
    ) -> dict[str, Any]:
        from devices.serial_device import SerialDevice

        device = SerialDevice(
            device_id=device_id,
            port=port,
            baudrate=baudrate,
            ownership_declared=ownership_declared,
        )
        try:
            device.connect()
        except Exception as exc:
            self._event_bus.publish(
                DeviceConnectionFailedEvent(device_id=device_id, reason=str(exc))
            )
            raise
        self._device_api.register(device)
        return {"device_id": device_id, "transport": "serial", **device.status()}

    def list_devices(self) -> list[dict[str, Any]]:
        return self._device_api.list()

    def get_device(self, device_id: str) -> Any | None:
        return self._device_api.get(device_id)

    def write_device(self, device_id: str, value: Any) -> dict[str, Any]:
        device = self._device_api.get(device_id)
        if device is None:
            raise RuntimeError(f"No such device: {device_id}")
        device.write(value)
        self._event_bus.publish(DeviceWriteEvent(device_id=device_id, value=str(value)))
        return {"device_id": device_id, "status": device.status()}

    def disconnect_device(self, device_id: str) -> dict[str, Any]:
        device = self._device_api.get(device_id)
        if device is None:
            raise RuntimeError(f"No such device: {device_id}")
        device.disconnect()
        self._device_api.unregister(device_id)
        return {"device_id": device_id, "status": "disconnected"}
