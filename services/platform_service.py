from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from contracts.agent import AgentApi
from contracts.capability import CapabilityApi
from contracts.device import DeviceApi
from contracts.event_bus import EventBus
from contracts.memory import MemoryApi
from contracts.plugin import PluginApi
from contracts.reasoning import ReasoningApi
from core.logger import get_logger
from core.observability import ObservabilityStore
from api.events import DeviceConnectionFailedEvent, DeviceWriteEvent
from reasoning.pipeline import ReasoningPipeline
from simulation.engine import SimulationEngine
from services.digital_device_service import DigitalDeviceService

logger = get_logger(__name__)


class PlatformService:
    def __init__(
        self,
        plugin_api: PluginApi,
        agent_api: AgentApi,
        capability_api: CapabilityApi,
        device_api: DeviceApi,
        memory_api: MemoryApi,
        reasoning_api: ReasoningApi,
        event_bus: EventBus,
        simulation_engine: SimulationEngine | None = None,
        reasoning_pipeline: ReasoningPipeline | None = None,
        observability: ObservabilityStore | None = None,
    ):
        self._plugin_api = plugin_api
        self._agent_api = agent_api
        self._capability_api = capability_api
        self._device_api = device_api
        self._memory_api = memory_api
        self._reasoning_api = reasoning_api
        self._event_bus = event_bus
        self._simulation_engine = simulation_engine or SimulationEngine()
        self._reasoning_pipeline = reasoning_pipeline or ReasoningPipeline()
        self._observability = observability

    def run_plugin(self, db: Session, plugin_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._trace("plugin.run", {"plugin_name": plugin_name})
        context = {"db": db, "logger": logger, **payload}
        return self._plugin_api.run(plugin_name, context)

    def dispatch_agent(
        self, db: Session, agent_name: str, task: dict[str, Any]
    ) -> dict[str, Any]:
        self._trace("agent.dispatch", {"agent_name": agent_name})
        context = {"db": db, "logger": logger}
        return self._agent_api.dispatch(agent_name, task, context)

    def store_memory(
        self, db: Session, content: str, tag: str = "general", source: str = "api"
    ) -> Any:
        self._trace("memory.store", {"tag": tag, "source": source})
        return self._memory_api.remember(db, content=content, tag=tag, source=source)

    def get_memory(self, db: Session, tag: str | None = None, limit: int = 50) -> list[Any]:
        return self._memory_api.recall(db, tag=tag, limit=limit)

    def store_fact(self, db: Session, subject: str, predicate: str, obj: str) -> Any:
        self._trace("reasoning.assert_fact", {"subject": subject, "predicate": predicate})
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
        self._register_device_capabilities(device_id)
        self._trace("device.register", {"device_id": device_id, "transport": "simulated"})
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
        self._register_device_capabilities(device_id)
        self._trace("device.register", {"device_id": device_id, "transport": "serial"})
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
        self._trace("device.write", {"device_id": device_id})
        return {"device_id": device_id, "status": device.status()}

    def disconnect_device(self, device_id: str) -> dict[str, Any]:
        device = self._device_api.get(device_id)
        if device is None:
            raise RuntimeError(f"No such device: {device_id}")
        device.disconnect()
        self._device_api.unregister(device_id)
        self._trace("device.disconnect", {"device_id": device_id})
        return {"device_id": device_id, "status": "disconnected"}

    def list_capabilities(
        self, prefix: str | None = None, target: str | None = None
    ) -> list[dict[str, Any]]:
        return self._capability_api.discover(prefix=prefix, target=target)

    def execute_capability(
        self,
        capability_name: str,
        payload: dict[str, Any],
        granted_permissions: set[str],
    ) -> Any:
        return self._capability_api.execute(
            capability_name, payload=payload, granted_permissions=granted_permissions
        )

    def capability_history(self, capability_name: str | None = None) -> list[dict[str, Any]]:
        return self._capability_api.history(capability_name=capability_name)

    def digital_device(self, db: Session, device_id: str) -> dict[str, Any]:
        service = DigitalDeviceService(
            device_api=self._device_api,
            memory_api=self._memory_api,
            reasoning_api=self._reasoning_api,
        )
        return service.build(db, device_id)

    def run_beta_workflow(
        self,
        db: Session,
        device_id: str,
        failure_mode: str,
        execute: bool = False,
        permissions: set[str] | None = None,
    ) -> dict[str, Any]:
        permissions = permissions or set()
        digital_device = self.digital_device(db, device_id)
        simulation_result = self._simulation_engine.simulate(
            device_id=device_id,
            device_state=digital_device["twin"]["hardware"],
            failure_mode=failure_mode,
        )
        reasoning = self._reasoning_pipeline.evaluate(simulation_result, device_id=device_id)
        recommendation = reasoning["recommendation"]
        execution_result = None
        if execute:
            execution_result = self.execute_capability(
                capability_name=recommendation["recommended_capability"],
                payload={},
                granted_permissions=permissions,
            )

        self._memory_api.remember(
            db,
            content=(
                f"Beta workflow simulation for {device_id}: "
                f"failure={failure_mode}, risk={simulation_result['risk']}"
            ),
            tag=device_id,
            source="beta_workflow",
        )
        self._reasoning_api.assert_fact(
            db,
            subject=device_id,
            predicate="event",
            obj=f"beta_simulation:{failure_mode}:{simulation_result['risk']}",
        )
        self._trace(
            "beta.workflow",
            {"device_id": device_id, "failure_mode": failure_mode, "execute": execute},
        )
        return {
            "digital_device": digital_device,
            "simulation": simulation_result,
            "reasoning": reasoning,
            "execution": execution_result,
            "recorded": True,
        }

    def _register_device_capabilities(self, device_id: str) -> None:
        prefix = f"device.{device_id}"

        self._register_capability_if_missing(
            name=f"{prefix}.connect",
            target=f"device:{device_id}",
            description="Connect to device",
            permissions={"device.connect"},
            executor=lambda _: self._device_action(device_id, "connect"),
        )
        self._register_capability_if_missing(
            name=f"{prefix}.disconnect",
            target=f"device:{device_id}",
            description="Disconnect from device",
            permissions={"device.disconnect"},
            executor=lambda _: self._device_action(device_id, "disconnect"),
        )
        self._register_capability_if_missing(
            name=f"{prefix}.read",
            target=f"device:{device_id}",
            description="Read current value from device",
            permissions={"device.read"},
            executor=lambda _: {"value": self._device_action(device_id, "read")},
        )
        self._register_capability_if_missing(
            name=f"{prefix}.write",
            target=f"device:{device_id}",
            description="Write payload value to device",
            permissions={"device.write"},
            executor=lambda payload: self._write_capability(device_id, payload),
        )
        self._register_capability_if_missing(
            name=f"{prefix}.status",
            target=f"device:{device_id}",
            description="Get current device status",
            permissions={"device.status"},
            executor=lambda _: self._device_action(device_id, "status"),
        )
        self._register_capability_if_missing(
            name=f"{prefix}.diagnose",
            target=f"device:{device_id}",
            description="Run device diagnostics",
            permissions={"device.diagnose"},
            executor=lambda _: self._device_action(device_id, "diagnose"),
        )
        self._register_capability_if_missing(
            name=f"{prefix}.recover",
            target=f"device:{device_id}",
            description="Run device recovery routine",
            permissions={"device.recover"},
            executor=lambda _: self._device_action(device_id, "recover"),
        )
        self._register_capability_if_missing(
            name=f"{prefix}.simulate",
            target=f"device:{device_id}",
            description="Execute simulated failure/readback cycle",
            permissions={"device.simulate"},
            executor=lambda payload: self._simulate_capability(device_id, payload),
        )

    def _register_capability_if_missing(
        self,
        name: str,
        target: str,
        description: str,
        permissions: set[str],
        executor,
    ) -> None:
        if self._capability_api.exists(name):
            return
        self._capability_api.register(
            name=name,
            target=target,
            description=description,
            permissions=permissions,
            executor=executor,
        )

    def _device_action(self, device_id: str, action: str) -> Any:
        device = self._device_api.get(device_id)
        if device is None:
            raise RuntimeError(f"No such device: {device_id}")
        method = getattr(device, action)
        result = method()
        if action in {"connect", "disconnect"}:
            return device.status()
        return result

    def _write_capability(self, device_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if "value" not in payload:
            raise ValueError("Capability payload must include 'value' for device.write")
        return self.write_device(device_id=device_id, value=payload["value"])

    def _simulate_capability(self, device_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        device = self._device_api.get(device_id)
        if device is None:
            raise RuntimeError(f"No such device: {device_id}")
        if device.transport != "simulated":
            raise RuntimeError(
                f"device.{device_id}.simulate is only supported for simulated devices"
            )
        write_value = payload.get("write", "simulated")
        device.write(write_value)
        return {"status": device.status(), "readback": device.read()}

    def _trace(self, name: str, detail: dict[str, Any]) -> None:
        if self._observability is not None:
            self._observability.record_trace(name, detail)
