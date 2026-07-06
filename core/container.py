from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


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

    def list_services(self) -> list[str]:
        return list(self._services.keys())
