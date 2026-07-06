from abc import ABC, abstractmethod
from collections.abc import Callable


class SchedulerApi(ABC):
    @abstractmethod
    def schedule(self, name: str, func: Callable[[], None], interval_seconds: int) -> None: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def list_jobs(self) -> list[str]: ...
