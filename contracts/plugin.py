from abc import ABC, abstractmethod
from typing import Any


class PluginApi(ABC):
    @abstractmethod
    def register(self, plugin: Any) -> None: ...

    @abstractmethod
    def get(self, name: str) -> Any | None: ...

    @abstractmethod
    def list_plugins(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def run(self, name: str, context: dict[str, Any]) -> dict[str, Any]: ...
