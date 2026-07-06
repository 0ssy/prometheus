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

    recovery_devices = engine.query.devices_supporting_recovery(db_session)
    failed = engine.query.simulations_failed(db_session)
    never_executed = engine.query.capabilities_never_executed(db_session)
    learning = engine.learning.recall(db_session, scenario_key="devx:disconnect")

    assert "device.devx" in recovery_devices
    assert any(row["device"] == "device.devx" for row in failed)
    assert "device.devx.recover" not in never_executed
    assert len(learning) == 1
