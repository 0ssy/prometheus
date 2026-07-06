from reasoning.pipeline import ReasoningPipeline


def test_reasoning_pipeline_produces_recommendation():
    pipeline = ReasoningPipeline()
    result = pipeline.evaluate(
        simulation_result={
            "failure_mode": "disconnect",
            "impact": "device_offline",
            "risk": "high",
            "recovered": False,
        },
        device_id="dev-r",
    )

    assert "observation" in result
    assert "hypothesis" in result
    assert "plan" in result
    assert "verification" in result
    assert result["recommendation"]["recommended_capability"] == "device.dev-r.recover"
