from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class CapabilityApi(ABC):
    @abstractmethod
    def register(
        self,
        name: str,
        target: str,
        description: str,
        permissions: set[str],
        executor: Callable[[dict[str, Any]], Any],
    ) -> None: ...

    @abstractmethod
    def exists(self, name: str) -> bool: ...

    @abstractmethod
    def discover(
        self, prefix: str | None = None, target: str | None = None
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def authorize(self, name: str, granted_permissions: set[str]) -> bool: ...

    @abstractmethod
    def execute(
        self,
        name: str,
        payload: dict[str, Any],
        granted_permissions: set[str],
    ) -> Any: ...

    @abstractmethod
    def history(self, capability_name: str | None = None) -> list[dict[str, Any]]: ...
