from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class SchedulerApi(ABC):
    @abstractmethod
    def schedule(self, name: str, func: Callable[[], None], interval_seconds: int) -> None: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def list_jobs(self) -> list[str]: ...

    @abstractmethod
    def jobs_detail(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def pause(self, name: str) -> None: ...

    @abstractmethod
    def resume(self, name: str) -> None: ...

    @abstractmethod
    def trigger(self, name: str) -> None: ...
