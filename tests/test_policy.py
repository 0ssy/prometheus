from __future__ import annotations

from omega.policy import (
    PermissionHierarchy,
    PolicyAuditLogger,
    PolicyEngine,
    RuleEngine,
)
from omega.policy.authorization import PolicyContext
from omega.policy.permissions import Permission
from omega.policy.rules import PolicyRule, RuleCondition


def test_policy_engine_evaluate_allow():
    engine = PolicyEngine()
    engine.add_rule(
        {
            "rule_id": "r1",
            "name": "allow-recover",
            "effect": "allow",
            "actions": ["device.recover"],
            "resources": ["device/1"],
            "priority": 10,
        }
    )
    decision = engine.evaluate(
        PolicyContext(actor="alice", action="device.recover", resource="device/1")
    )
    assert decision.allowed is True
    assert decision.matched_rule == "allow-recover"


def test_policy_engine_evaluate_deny():
    engine = PolicyEngine()
    engine.add_rule(
        {
            "rule_id": "r1",
            "name": "deny-flash",
            "effect": "deny",
            "actions": ["device.flash"],
            "resources": ["device/1"],
            "priority": 10,
        }
    )
    decision = engine.evaluate(
        PolicyContext(actor="mallory", action="device.flash", resource="device/1")
    )
    assert decision.allowed is False
    assert decision.matched_rule == "deny-flash"


def test_policy_engine_add_rule():
    engine = PolicyEngine()
    engine.add_rule({"rule_id": "x", "name": "r", "effect": "allow", "actions": ["a"], "resources": ["b"]})
    assert len(engine.list_rules()) == 1
    assert engine.remove_rule("x") is True
    assert len(engine.list_rules()) == 0


def test_permission_hierarchy_register():
    hierarchy = PermissionHierarchy()
    hierarchy.register(Permission(name="device.read", description="read", category="device"))
    assert "device.read" in hierarchy._permissions
    try:
        hierarchy.register(Permission(name="device.read", description="dup", category="device"))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_permission_hierarchy_effective():
    hierarchy = PermissionHierarchy()
    hierarchy.register(Permission(name="device.read", description="read", category="device"))
    hierarchy.register(Permission(name="device.write", description="write", category="device"))
    effective = hierarchy.effective_permissions("alice")
    assert effective == {"device.read", "device.write"}


def test_rule_engine_add_and_evaluate():
    engine = RuleEngine()
    engine.add_rule(
        PolicyRule(
            rule_id="rr1",
            name="r1",
            description="d",
            effect="deny",
            actions=["flash"],
            resources=["*"],
            conditions=[RuleCondition(field="actor", operator="eq", value="mallory")],
            priority=5,
        )
    )
    matches = engine.evaluate(PolicyContext(actor="mallory", action="flash", resource="device/1"))
    assert len(matches) == 1
    assert matches[0].rule_id == "rr1"


def test_policy_audit_logger_record_and_query():
    logger = PolicyAuditLogger()
    logger.record("alice", "device.recover", "device/1", "allow", matched_rules=["r1"])
    logger.record("mallory", "device.flash", "device/2", "deny", matched_rules=["r2"])
    assert len(logger.query()) == 2
    alice_entries = logger.query(actor="alice")
    assert len(alice_entries) == 1
    assert alice_entries[0].actor == "alice"
    flash_entries = logger.query(action="device.flash")
    assert len(flash_entries) == 1
    assert flash_entries[0].decision == "deny"
