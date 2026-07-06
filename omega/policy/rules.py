from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RuleCondition:
    field: str
    operator: str
    value: Any


@dataclass
class PolicyRule:
    rule_id: str
    name: str
    description: str
    effect: str = "deny"
    actions: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    conditions: list[RuleCondition] = field(default_factory=list)
    priority: int = 0


class RuleEngine:
    def __init__(self) -> None:
        self._rules: list[PolicyRule] = []
        self._lock = threading.RLock()

    def add_rule(self, rule: PolicyRule) -> None:
        with self._lock:
            self._rules.append(rule)

    def evaluate(self, context: Any) -> list[PolicyRule]:
        with self._lock:
            matching = []
            for rule in self._rules:
                if self._matches(context, rule):
                    matching.append(rule)
            return sorted(matching, key=lambda r: r.priority, reverse=True)

    def compile(self) -> None:
        with self._lock:
            self._rules.sort(key=lambda r: r.priority, reverse=True)

    def _matches(self, context: Any, rule: PolicyRule) -> bool:
        return True


import threading
