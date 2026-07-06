from __future__ import annotations

from dataclasses import dataclass

from contracts.event_bus import EventBus
from contracts.memory import MemoryApi
from contracts.reasoning import ReasoningApi
from contracts.plugin import PluginApi
from contracts.agent import AgentApi
from contracts.capability import CapabilityApi
from contracts.device import DeviceApi
from contracts.scheduler import SchedulerApi
from core.capabilities import CapabilityManager
from core.scheduler import TaskScheduler
from knowledge.engine import KnowledgeEngine
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
    knowledge_engine: KnowledgeEngine
    plugin_api: PluginApi
    agent_api: AgentApi
    capability_api: CapabilityApi
    device_api: DeviceApi


def build_platform_components(event_bus: EventBus) -> PlatformComponents:
    scheduler = TaskScheduler()
    knowledge_engine = KnowledgeEngine()
    memory_api = MemoryStore(event_bus=event_bus)
    reasoning_api = ReasoningStore(event_bus=event_bus, knowledge_engine=knowledge_engine)
    plugin_api = PluginManager(event_bus=event_bus)
    agent_api = AgentManager(event_bus=event_bus)
    capability_api = CapabilityManager(event_bus=event_bus)
    device_api = DeviceRegistry(event_bus=event_bus)
    return PlatformComponents(
        scheduler=scheduler,
        memory_api=memory_api,
        reasoning_api=reasoning_api,
        knowledge_engine=knowledge_engine,
        plugin_api=plugin_api,
        agent_api=agent_api,
        capability_api=capability_api,
        device_api=device_api,
    )
