from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy.orm import Session


class MemoryApi(ABC):
    @abstractmethod
    def remember(
        self, db: Session, content: str, tag: str = "general", source: str = "system"
    ) -> Any: ...

    @abstractmethod
    def recall(
        self, db: Session, tag: str | None = None, limit: int = 50
    ) -> list[Any]: ...
