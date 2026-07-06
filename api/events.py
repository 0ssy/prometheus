from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Event:
    event_type: str = ""
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class PluginRanEvent(Event):
    plugin_name: str
    result: dict

    def __post_init__(self) -> None:
        self.event_type = "plugin.ran"


@dataclass
class AgentDispatchedEvent(Event):
    agent_name: str
    task: dict

    def __post_init__(self) -> None:
        self.event_type = "agent.dispatched"


@dataclass
class DeviceConnectedEvent(Event):
    device_id: str
    transport: str

    def __post_init__(self) -> None:
        self.event_type = "device.connected"


@dataclass
class DeviceDisconnectedEvent(Event):
    device_id: str

    def __post_init__(self) -> None:
        self.event_type = "device.disconnected"


@dataclass
class MemoryStoredEvent(Event):
    content: str
    tag: str
    source: str

    def __post_init__(self) -> None:
        self.event_type = "memory.stored"


@dataclass
class FactAssertedEvent(Event):
    subject: str
    predicate: str
    obj: str
    confidence: int = 100

    def __post_init__(self) -> None:
        self.event_type = "fact.asserted"
