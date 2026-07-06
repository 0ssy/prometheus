from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from contracts.event_bus import EventBus
from api.events import Event
from core.logger import get_logger

logger = get_logger(__name__)


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
        logger.info(f"Subscribed handler for event: {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)

    def publish(self, event: Event) -> None:
        event_type = event.event_type
        # Snapshot handlers so high-volume publishing is stable even if
        # subscribers change while events are flowing.
        handlers = list(self._subscribers.get(event_type, []))
        for handler in handlers:
            handler(event)


event_bus = InMemoryEventBus()
