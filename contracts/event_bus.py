from abc import ABC, abstractmethod
from collections.abc import Callable

from api.events import Event


class EventBus(ABC):
    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None: ...

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> None: ...

    @abstractmethod
    def publish(self, event: Event) -> None: ...
