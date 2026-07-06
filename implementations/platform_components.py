from __future__ import annotations

from dataclasses import dataclass

from contracts.event_bus import EventBus
from contracts.memory import MemoryApi
from contracts.reasoning import ReasoningApi
from contracts.plugin import PluginApi
from contracts.agent import AgentApi
from contracts.device import DeviceApi
from contracts.scheduler import SchedulerApi
from core.scheduler import TaskScheduler
from memory.store import MemoryStore
from reasoning.graph import ReasoningStore
from plugins.manager import PluginManager
from agents.manager import AgentManager
from devices.registry import DeviceRegistry


@dataclass
class PlatformComponents:
    scheduler: SchedulerApi
    memory_api: MemoryApi
    reasoning_api: ReasoningApi
    plugin_api: PluginApi
    agent_api: AgentApi
    device_api: DeviceApi


def build_platform_components(event_bus: EventBus) -> PlatformComponents:
    scheduler = TaskScheduler()
    memory_api = MemoryStore(event_bus=event_bus)
    reasoning_api = ReasoningStore(event_bus=event_bus)
    plugin_api = PluginManager(event_bus=event_bus)
    agent_api = AgentManager(event_bus=event_bus)
    device_api = DeviceRegistry(event_bus=event_bus)
    return PlatformComponents(
        scheduler=scheduler,
        memory_api=memory_api,
        reasoning_api=reasoning_api,
        plugin_api=plugin_api,
        agent_api=agent_api,
        device_api=device_api,
    )
