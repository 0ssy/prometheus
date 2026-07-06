from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy.orm import Session


class ReasoningApi(ABC):
    @abstractmethod
    def assert_fact(
        self, db: Session, subject: str, predicate: str, obj: str, confidence: int = 100
    ) -> Any: ...

    @abstractmethod
    def query_facts(
        self, db: Session, subject: str | None = None, predicate: str | None = None
    ) -> list[Any]: ...
