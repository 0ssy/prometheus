from services.omega_service import OmegaService


def test_omega_service_marketplace_and_collaboration():
    omega = OmegaService()
    omega.publish_plugin({"name": "p1", "version": "1.0.0"})
    assert len(omega.list_plugins()) == 1
    plan = omega.plan_collaboration(["recover device", "collect telemetry"])
    assert len(plan["assignments"]) == 2


def test_omega_service_distributed_policy_and_api_catalog():
    omega = OmegaService()
    omega.register_node("node-a")
    assert "node-a" in omega.list_nodes()["nodes"]
    omega.grant_permission("alice", "device.recover")
    assert omega.check_permission("alice", "device.recover")["allowed"] is True
    assert "REST API" in omega.public_apis()["apis"]


def test_omega_service_coordinate_agents():
    omega = OmegaService()
    result = omega.coordinate_agents(
        [{"task_id": "t1", "description": "recover device"}]
    )
    assert len(result["results"]) == 1
    assert result["results"][0]["task_id"] == "t1"
    assert result["results"][0]["status"] == "pending"


def test_omega_service_plan_tasks():
    omega = OmegaService()
    plan = omega.plan_tasks("build firmware", ["recovery_agent", "hardware_agent"], {"cap": []})
    assert plan["objective"] == "build firmware"
    assert "root" in plan["tasks"]


def test_omega_service_consensus():
    omega = OmegaService()
    proposed = omega.consensus_propose({"id": "p1", "action": "recover"}, ["a", "b"])
    assert proposed["decision"] == "pending"
    assert proposed["participating_agents"] == ["a", "b"]


def test_omega_service_delegate():
    omega = OmegaService()
    result = omega.delegate_task("agent-a", "agent-b", {"task": "recover"})
    assert result["success"] is True
    assert result["result"]["delegated_to"] == "agent-b"


def test_omega_service_dashboard():
    omega = OmegaService()
    overview = omega.get_dashboard("overview")
    assert overview["platform"] == "Prometheus"
    assert overview["status"] == "ok"
    sections = omega.get_dashboard()
    assert "platform" in sections
