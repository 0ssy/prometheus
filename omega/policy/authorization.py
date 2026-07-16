from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import threading

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    matched_rule: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PolicyContext:
    actor: str
    action: str
    resource: str
    environment: dict[str, Any] = field(default_factory=dict)
    permissions: set[str] = field(default_factory=set)


class PolicyEngine:
    def __init__(self) -> None:
        self._rules: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        with self._lock:
            for rule in sorted(self._rules, key=lambda r: r.get("priority", 0), reverse=True):
                if self._matches(context, rule):
                    allowed = rule.get("effect", "deny") == "allow"
                    return PolicyDecision(
                        allowed=allowed,
                        reason=f"Matched rule: {rule.get('name', 'unnamed')}",
                        matched_rule=rule.get("name"),
                    )
        return PolicyDecision(allowed=False, reason="No matching policy rule")

    def add_rule(self, rule: dict[str, Any]) -> None:
        with self._lock:
            self._rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        with self._lock:
            for i, rule in enumerate(self._rules):
                if rule.get("rule_id") == rule_id:
                    self._rules.pop(i)
                    return True
            return False

    def list_rules(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._rules)

    def _matches(self, context: PolicyContext, rule: dict[str, Any]) -> bool:
        if rule.get("actions") and context.action not in rule["actions"]:
            return False
        if rule.get("resources") and context.resource not in rule["resources"]:
            return False
        return True


