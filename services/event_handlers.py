from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from api.events import (
    AgentDispatchedEvent,
    DeviceConnectedEvent,
    DeviceConnectionFailedEvent,
    DeviceDisconnectedEvent,
    DeviceWriteEvent,
    MemoryStoredEvent,
    PluginRanEvent,
    FactAssertedEvent,
    CapabilityExecutedEvent,
)
from contracts.event_bus import EventBus
from contracts.memory import MemoryApi
from contracts.reasoning import ReasoningApi
from core.logger import get_logger
from core.observability import ObservabilityStore

logger = get_logger(__name__)


class PlatformEventHandlers:
    def __init__(
        self,
        event_bus: EventBus,
        session_factory: Callable[[], Session],
        memory_api: MemoryApi,
        reasoning_api: ReasoningApi,
        observability: ObservabilityStore | None = None,
    ):
        self._event_bus = event_bus
        self._session_factory = session_factory
        self._memory_api = memory_api
        self._reasoning_api = reasoning_api
        self._observability = observability

    def bind(self) -> None:
        self._event_bus.subscribe("device.connected", self._on_device_connected)
        self._event_bus.subscribe("device.disconnected", self._on_device_disconnected)
        self._event_bus.subscribe("device.connect_failed", self._on_device_connect_failed)
        self._event_bus.subscribe("device.wrote", self._on_device_wrote)
        self._event_bus.subscribe("plugin.ran", self._on_plugin_ran)
        self._event_bus.subscribe("agent.dispatched", self._on_agent_dispatched)
        self._event_bus.subscribe("memory.stored", self._on_memory_stored)
        self._event_bus.subscribe("fact.asserted", self._on_fact_asserted)
        self._event_bus.subscribe("capability.executed", self._on_capability_executed)

    def _with_session(self, operation: Callable[[Session], Any]) -> Any:
        session = self._session_factory()
        try:
            return operation(session)
        finally:
            session.close()

    def _on_device_connected(self, event: DeviceConnectedEvent) -> None:
        def operation(session: Session) -> None:
            self._reasoning_api.assert_fact(
                session, subject=event.device_id, predicate="event", obj="connected"
            )

        self._with_session(operation)

    def _on_device_disconnected(self, event: DeviceDisconnectedEvent) -> None:
        def operation(session: Session) -> None:
            self._reasoning_api.assert_fact(
                session, subject=event.device_id, predicate="event", obj="disconnected"
            )

        self._with_session(operation)

    def _on_device_connect_failed(self, event: DeviceConnectionFailedEvent) -> None:
        def operation(session: Session) -> None:
            self._reasoning_api.assert_fact(
                session,
                subject=event.device_id,
                predicate="event",
                obj=f"connect_failed:{event.reason}",
            )

        self._with_session(operation)

    def _on_device_wrote(self, event: DeviceWriteEvent) -> None:
        def operation(session: Session) -> None:
            self._reasoning_api.assert_fact(
                session, subject=event.device_id, predicate="wrote", obj=event.value
            )

        self._with_session(operation)

    def _on_plugin_ran(self, event: PluginRanEvent) -> None:
        def operation(session: Session) -> None:
            summary = f"Plugin {event.plugin_name} ran with result keys: {sorted(event.result.keys())}"
            self._memory_api.remember(
                session, content=summary, tag="plugin_event", source="event_bus"
            )

        self._with_session(operation)

    def _on_agent_dispatched(self, event: AgentDispatchedEvent) -> None:
        def operation(session: Session) -> None:
            self._reasoning_api.assert_fact(
                session,
                subject=event.agent_name,
                predicate="event",
                obj="dispatched",
            )

        self._with_session(operation)

    def _on_memory_stored(self, event: MemoryStoredEvent) -> None:
        self._record_event("memory.stored", {"tag": event.tag, "source": event.source})
        logger.info(
            "Memory event observed: tag=%s source=%s", event.tag, event.source
        )

    def _on_fact_asserted(self, event: FactAssertedEvent) -> None:
        self._record_event(
            "fact.asserted",
            {"subject": event.subject, "predicate": event.predicate, "obj": event.obj},
        )

    def _on_capability_executed(self, event: CapabilityExecutedEvent) -> None:
        self._record_event(
            "capability.executed",
            {"capability_name": event.capability_name, "success": event.success},
        )

    def _record_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._observability is not None:
            self._observability.record_event(event_type, payload)
