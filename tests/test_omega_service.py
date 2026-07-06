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
