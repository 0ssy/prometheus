from abc import ABC, abstractmethod
from typing import Any


class EventBus(ABC):
    @abstractmethod
    def subscribe(self, event_type: str, handler: Any) -> None:
        ...

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: Any) -> None:
        ...

    @abstractmethod
    def publish(self, event: Any) -> None:
        ...
