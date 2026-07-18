from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


class VectorClock:
    def __init__(self) -> None:
        self._clocks: dict[str, int] = {}

    def increment(self, node_id: str) -> None:
        self._clocks[node_id] = self._clocks.get(node_id, 0) + 1

    def get(self, node_id: str) -> int:
        return self._clocks.get(node_id, 0)

    def merge(self, other: VectorClock) -> None:
        for node_id, count in other._clocks.items():
            self._clocks[node_id] = max(self._clocks.get(node_id, 0), count)

    def to_dict(self) -> dict[str, int]:
        return dict(self._clocks)

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> VectorClock:
        vc = cls()
        vc._clocks = dict(data)
        return vc


class GCounter:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def increment(self, node_id: str, amount: int = 1) -> None:
        self._counts[node_id] = self._counts.get(node_id, 0) + amount

    def value(self) -> int:
        return sum(self._counts.values())

    def merge(self, other: GCounter) -> None:
        for node_id, count in other._counts.items():
            self._counts[node_id] = max(self._counts.get(node_id, 0), count)

    def to_dict(self) -> dict[str, int]:
        return dict(self._counts)

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> GCounter:
        counter = cls()
        counter._counts = dict(data)
        return counter


class PNCounter:
    def __init__(self) -> None:
        self._positive = GCounter()
        self._negative = GCounter()

    def increment(self, node_id: str, amount: int = 1) -> None:
        self._positive.increment(node_id, amount)

    def decrement(self, node_id: str, amount: int = 1) -> None:
        self._negative.increment(node_id, amount)

    def value(self) -> int:
        return self._positive.value() - self._negative.value()

    def merge(self, other: PNCounter) -> None:
        self._positive.merge(other._positive)
        self._negative.merge(other._negative)

    def to_dict(self) -> dict[str, Any]:
        return {
            "positive": self._positive.to_dict(),
            "negative": self._negative.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PNCounter:
        counter = cls()
        counter._positive = GCounter.from_dict(data.get("positive", {}))
        counter._negative = GCounter.from_dict(data.get("negative", {}))
        return counter


class GSet:
    def __init__(self) -> None:
        self._elements: set[str] = set()

    def add(self, element: str) -> None:
        self._elements.add(element)

    def remove(self, element: str) -> None:
        pass

    def has(self, element: str) -> bool:
        return element in self._elements

    def elements(self) -> set[str]:
        return set(self._elements)

    def merge(self, other: GSet) -> None:
        self._elements.update(other._elements)

    def to_dict(self) -> list[str]:
        return list(self._elements)

    @classmethod
    def from_dict(cls, data: list[str]) -> GSet:
        gset = cls()
        gset._elements = set(data)
        return gset


class LWWRegister:
    def __init__(self) -> None:
        self._value: Any = None
        self._timestamp: float = 0.0
        self._node_id: str = ""

    def set(self, value: Any, timestamp: float | None = None, node_id: str = "") -> None:
        if timestamp is None:
            timestamp = time.time()
        if timestamp > self._timestamp or (timestamp == self._timestamp and node_id > self._node_id):
            self._value = value
            self._timestamp = timestamp
            self._node_id = node_id

    def get(self) -> Any:
        return self._value

    def merge(self, other: LWWRegister) -> None:
        if other._timestamp > self._timestamp or (
            other._timestamp == self._timestamp and other._node_id > self._node_id
        ):
            self._value = other._value
            self._timestamp = other._timestamp
            self._node_id = other._node_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self._value,
            "timestamp": self._timestamp,
            "node_id": self._node_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LWWRegister:
        reg = cls()
        reg._value = data.get("value")
        reg._timestamp = data.get("timestamp", 0.0)
        reg._node_id = data.get("node_id", "")
        return reg


class ORSet:
    def __init__(self) -> None:
        self._elements: dict[str, set[str]] = {}
        self._removed: set[str] = set()

    def _generate_tag(self) -> str:
        return str(uuid.uuid4())

    def add(self, element: str) -> None:
        tag = self._generate_tag()
        if element not in self._elements:
            self._elements[element] = set()
        self._elements[element].add(tag)

    def remove(self, element: str) -> None:
        if element in self._elements:
            self._removed.update(self._elements[element])
            del self._elements[element]

    def has(self, element: str) -> bool:
        if element not in self._elements:
            return False
        return bool(self._elements[element] - self._removed)

    def elements(self) -> set[str]:
        result: set[str] = set()
        for element, tags in self._elements.items():
            if tags - self._removed:
                result.add(element)
        return result

    def merge(self, other: ORSet) -> None:
        for element, tags in other._elements.items():
            if element not in self._elements:
                self._elements[element] = set()
            self._elements[element].update(tags)
        self._removed.update(other._removed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "elements": {k: list(v) for k, v in self._elements.items()},
            "removed": list(self._removed),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ORSet:
        orset = cls()
        orset._elements = {k: set(v) for k, v in data.get("elements", {}).items()}
        orset._removed = set(data.get("removed", []))
        return orset


@dataclass
class CrdtNode:
    node_id: str
    vector_clock: VectorClock = field(default_factory=VectorClock)
    counter: PNCounter = field(default_factory=PNCounter)
    set: ORSet = field(default_factory=ORSet)
    register: LWWRegister = field(default_factory=LWWRegister)
    timestamp: float = field(default_factory=time.time)

    def merge(self, other: CrdtNode) -> CrdtNode:
        self.vector_clock.merge(other.vector_clock)
        self.counter.merge(other.counter)
        self.set.merge(other.set)
        self.register.merge(other.register)
        self.timestamp = max(self.timestamp, other.timestamp)
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "vector_clock": self.vector_clock.to_dict(),
            "counter": self.counter.to_dict(),
            "set": self.set.to_dict(),
            "register": self.register.to_dict(),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CrdtNode:
        node = cls(
            node_id=data["node_id"],
            vector_clock=VectorClock.from_dict(data.get("vector_clock", {})),
            counter=PNCounter.from_dict(data.get("counter", {"positive": {}, "negative": {}})),
            set=ORSet.from_dict(data.get("set", {"elements": {}, "removed": []})),
            register=LWWRegister.from_dict(
                data.get("register", {"value": None, "timestamp": 0.0, "node_id": ""})
            ),
            timestamp=data.get("timestamp", 0.0),
        )
        return node
