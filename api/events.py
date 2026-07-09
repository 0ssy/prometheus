from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(kw_only=True)
class Event:
    event_type: str = field(default="", init=False)
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
class DeviceConnectionFailedEvent(Event):
    device_id: str
    reason: str

    def __post_init__(self) -> None:
        self.event_type = "device.connect_failed"


@dataclass
class DeviceWriteEvent(Event):
    device_id: str
    value: str

    def __post_init__(self) -> None:
        self.event_type = "device.wrote"


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


@dataclass
class CapabilityExecutedEvent(Event):
    capability_name: str
    success: bool

    def __post_init__(self) -> None:
        self.event_type = "capability.executed"


@dataclass
class AgentStatusChangedEvent(Event):
    agent_name: str
    status: str
    last_task: dict | None = None

    def __post_init__(self) -> None:
        self.event_type = "agent.status"
