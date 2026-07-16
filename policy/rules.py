from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import threading
import uuid

from core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class RuleCondition:
    field: str
    operator: str
    value: Any


@dataclass
class PolicyRule:
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    effect: str = "allow"
    actions: set[str] = field(default_factory=set)
    resources: set[str] = field(default_factory=set)
    conditions: dict[str, Any] = field(default_factory=dict)
    priority: int = 100


class RuleEngine:
    def __init__(self) -> None:
        self._rules: list[PolicyRule] = []
        self._lock = threading.RLock()
        self._compiled = False
        self._logger = get_logger(__name__)

    def add_rule(self, rule: PolicyRule) -> None:
        with self._lock:
            self._rules.append(rule)
            self._compiled = False
            self._logger.info(f"Added policy rule: {rule.rule_id} ({rule.name})")

    def remove_rule(self, rule_id: str) -> bool:
        with self._lock:
            before = len(self._rules)
            self._rules = [r for r in self._rules if r.rule_id != rule_id]
            changed = before != len(self._rules)
            if changed:
                self._compiled = False
            return changed

    def list_rules(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "description": r.description,
                    "effect": r.effect,
                    "actions": list(r.actions),
                    "resources": list(r.resources),
                    "conditions": r.conditions,
                    "priority": r.priority,
                }
                for r in self._rules
            ]

    def compile(self) -> None:
        with self._lock:
            self._rules.sort(key=lambda r: r.priority)
            self._compiled = True
            self._logger.info(f"Compiled {len(self._rules)} policy rules")

    def evaluate(self, context: Any) -> list[PolicyRule]:
        with self._lock:
            if not self._compiled:
                self.compile()
            matched: list[PolicyRule] = []
            for rule in self._rules:
                if rule.actions and context.action not in rule.actions:
                    continue
                if rule.resources and context.resource not in rule.resources:
                    continue
                if rule.conditions and not self._evaluate_conditions(rule.conditions, context):
                    continue
                matched.append(rule)
            return matched

    def _evaluate_conditions(self, conditions: dict[str, Any], context: Any) -> bool:
        for cond_field, value in conditions.items():
            if context.environment.get(cond_field) != value:
                return False
        return True
