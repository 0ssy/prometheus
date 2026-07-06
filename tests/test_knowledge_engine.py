from knowledge.engine import KnowledgeEngine


def test_knowledge_engine_records_and_queries(db_session):
    engine = KnowledgeEngine()
    engine.record_fact(
        db_session,
        subject="device.devx",
        predicate="supports_capability",
        obj="device.devx.recover",
        confidence=0.9,
    )
    engine.record_fact(
        db_session,
        subject="device.devx",
        predicate="simulation_outcome",
        obj="failed:disconnect:high",
        confidence=0.8,
    )
    engine.record_fact(
        db_session,
        subject="device.devx",
        predicate="capability_executed",
        obj="device.devx.recover",
        confidence=0.95,
    )
    engine.record_learning(
        db_session,
        scenario_key="devx:disconnect",
        outcome="attention_required",
        confidence=0.8,
        context={"risk": "high"},
    )

    recovery_devices = engine.query(db_session, "devices_supporting_recovery")
    failed = engine.query(db_session, "simulations_failed")
    never_executed = engine.query(db_session, "capabilities_never_executed")
    learning = engine.learning.recall(db_session, scenario_key="devx:disconnect")

    assert "device.devx" in recovery_devices
    assert any(row["device"] == "device.devx" for row in failed)
    assert "device.devx.recover" not in never_executed
    assert len(learning) == 1


def test_knowledge_engine_independent_usage_shape(db_session):
    engine = KnowledgeEngine()
    engine.assert_fact(
        db_session,
        subject="device.independent",
        predicate="supports_capability",
        obj="device.independent.recover",
        confidence=0.9,
        source="test",
        rationale="independent usage",
        evidence={"case": "shape"},
    )
    engine.learn(
        db_session,
        scenario_key="independent:disconnect",
        outcome="attention_required",
        confidence=0.7,
        context={"risk": "high"},
    )
    devices = engine.query(db_session, "devices_supporting_recovery")
    assert "device.independent" in devices
