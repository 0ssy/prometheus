from abc import ABC, abstractmethod
from typing import Any


class DeviceApi(ABC):
    @abstractmethod
    def register(self, device: Any) -> None: ...

    @abstractmethod
    def unregister(self, device_id: str) -> None: ...

    @abstractmethod
    def get(self, device_id: str) -> Any | None: ...

    @abstractmethod
    def list(self) -> list[dict[str, Any]]: ...
