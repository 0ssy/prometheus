from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.logger import get_logger
from policy.permissions import PermissionHierarchy
from policy.rules import PolicyRule, RuleEngine

logger = get_logger(__name__)


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    matched_rule: str | None
    timestamp: str


@dataclass
class PolicyContext:
    actor: str
    action: str
    resource: str
    environment: dict[str, Any]
    permissions: set[str]


class PolicyEngine:
    def __init__(self) -> None:
        self._rule_engine = RuleEngine()
        self._permission_hierarchy = PermissionHierarchy()
        self._logger = get_logger(__name__)

    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        effective = self._permission_hierarchy.effective_permissions(context.actor)
        _context_permissions = context.permissions | effective
        matching_rules = self._rule_engine.evaluate(context)
        for rule in matching_rules:
            if rule.actions and context.action not in rule.actions:
                continue
            if rule.resources and context.resource not in rule.resources:
                continue
            if rule.conditions and not self._evaluate_conditions(rule.conditions, context):
                continue
            if rule.effect == "allow":
                return PolicyDecision(
                    True, rule.description, rule.rule_id, _now()
                )
            if rule.effect == "deny":
                return PolicyDecision(
                    False, rule.description, rule.rule_id, _now()
                )
        return PolicyDecision(False, "No matching policy", None, _now())

    def _evaluate_conditions(self, conditions: dict[str, Any], context: PolicyContext) -> bool:
        for field, value in conditions.items():
            if context.environment.get(field) != value:
                return False
        return True

    def add_rule(self, rule: PolicyRule) -> None:
        self._rule_engine.add_rule(rule)

    def remove_rule(self, rule_id: str) -> bool:
        return self._rule_engine.remove_rule(rule_id)

    def list_rules(self) -> list[dict]:
        return self._rule_engine.list_rules()


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
