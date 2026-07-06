from typing import Any, TypeVar

from core.logger import get_logger

logger = get_logger(__name__)
T = TypeVar("T")


class ServiceContainer:
    def __init__(self):
        self._services: dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        self._services[name] = service
        logger.info(f"Registered service: {name}")

    def get(self, name: str) -> Any:
        if name not in self._services:
            raise KeyError(f"Service '{name}' not found in container")
        return self._services[name]

    def resolve(self, name: str, expected_type: type[T]) -> T:
        service = self.get(name)
        if not isinstance(service, expected_type):
            raise TypeError(
                f"Service '{name}' is {type(service).__name__}, "
                f"expected {expected_type.__name__}"
            )
        return service

    def list_services(self) -> list[str]:
        return list(self._services.keys())
