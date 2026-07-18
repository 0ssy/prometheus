from __future__ import annotations

from policy import (
    PermissionHierarchy,
    PolicyAuditLogger,
    PolicyEngine,
    RuleEngine,
)
from policy.authorization import PolicyContext
from policy.audit import PolicyAuditEntry
from policy.permissions import Permission
from policy.rules import PolicyRule


def test_policy_engine_evaluate_allow():
    engine = PolicyEngine()
    engine.add_rule(
        PolicyRule(
            rule_id="r1",
            name="allow-recover",
            description="allow recover",
            effect="allow",
            actions={"device.recover"},
            resources={"device/1"},
            priority=10,
        )
    )
    decision = engine.evaluate(
        PolicyContext(
            actor="alice",
            action="device.recover",
            resource="device/1",
            environment={},
            permissions=set(),
        )
    )
    assert decision.allowed is True
    assert decision.matched_rule == "r1"


def test_policy_engine_evaluate_deny():
    engine = PolicyEngine()
    engine.add_rule(
        PolicyRule(
            rule_id="r1",
            name="deny-flash",
            description="deny flash",
            effect="deny",
            actions={"device.flash"},
            resources={"device/1"},
            priority=10,
        )
    )
    decision = engine.evaluate(
        PolicyContext(
            actor="mallory",
            action="device.flash",
            resource="device/1",
            environment={},
            permissions=set(),
        )
    )
    assert decision.allowed is False
    assert decision.matched_rule == "r1"


def test_policy_engine_add_rule():
    engine = PolicyEngine()
    engine.add_rule(
        PolicyRule(rule_id="x", name="r", effect="allow", actions={"a"}, resources={"b"})
    )
    assert len(engine.list_rules()) == 1
    assert engine.remove_rule("x") is True
    assert len(engine.list_rules()) == 0


def test_permission_hierarchy_register():
    hierarchy = PermissionHierarchy()
    _ = Permission(name="device.read", description="read", category="device")
    hierarchy.grant("alice", "device.read")
    assert hierarchy.has("alice", "device.read") is True


def test_permission_hierarchy_effective():
    hierarchy = PermissionHierarchy()
    hierarchy.grant("alice", "device.read")
    hierarchy.grant("alice", "device.write")
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
            resources=["device/1"],
            conditions={"actor": "mallory"},
            priority=5,
        )
    )
    matches = engine.evaluate(
    PolicyContext(
        actor="mallory",
        action="flash",
        resource="device/1",
        environment={"actor": "mallory"},
        permissions=set(),
    )
    )
    assert len(matches) == 1
    assert matches[0].rule_id == "rr1"


def test_policy_audit_logger_record_and_query():
    logger = PolicyAuditLogger()
    logger.log(
        PolicyAuditEntry(
            actor="alice",
            action="device.recover",
            resource="device/1",
            decision=True,
            matched_rules=["r1"],
        )
    )
    logger.log(
        PolicyAuditEntry(
            actor="mallory",
            action="device.flash",
            resource="device/2",
            decision=False,
            matched_rules=["r2"],
        )
    )
    assert len(logger.query()) == 2
    alice_entries = logger.query(actor="alice")
    assert len(alice_entries) == 1
    assert alice_entries[0].actor == "alice"
    flash_entries = logger.query(action="device.flash")
    assert len(flash_entries) == 1
    assert flash_entries[0].decision is False
