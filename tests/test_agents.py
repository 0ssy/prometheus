from __future__ import annotations

import pytest

from omega.agents import AgentCoordinator, ConsensusEngine, DelegationRouter, TaskPlanner
from omega.agents.coordinator import AgentTask, TaskStatus
from omega.agents.consensus import VoteChoice


def test_agent_coordinator_create_task():
    coordinator = AgentCoordinator()
    result = coordinator.coordinate(
        [{"task_id": "t1", "description": "do thing", "required_capabilities": ["cap"], "priority": 3}]
    )
    assert len(result["results"]) == 1
    task = result["results"][0]
    assert task["task_id"] == "t1"
    assert task["description"] == "do thing"
    assert task["required_capabilities"] == ["cap"]
    assert task["priority"] == 3
    assert task["status"] == TaskStatus.PENDING.value


def test_agent_coordinator_coordinate():
    coordinator = AgentCoordinator()
    result = coordinator.coordinate(
        [
            {"task_id": "a", "description": "first"},
            {"task_id": "b", "description": "second", "assigned_agent": "agent-x"},
        ]
    )
    ids = [t["task_id"] for t in result["results"]]
    assert ids == ["a", "b"]


def test_task_planner_topological_sort():
    planner = TaskPlanner()
    graph = planner.plan("objective", ["agent1"], {"cap": []})
    graph.add_task("c", "third", ["a", "b"], 1.0)
    graph.add_task("a", "first", [], 0.5)
    graph.add_task("b", "second", ["a"], 0.5)
    order = graph.topological_sort()
    assert order.index("a") < order.index("b")
    assert order.index("b") < order.index("c")
    assert order.index("a") < order.index("c")


def test_task_planner_validate():
    planner = TaskPlanner()
    graph = planner.plan("objective", [], {})
    graph.add_task("a", "first", [], 0.0)
    graph.add_task("b", "second", ["missing"], 0.0)
    errors = graph.validate()
    assert len(errors) == 1
    assert "missing" in errors[0]


def test_consensus_engine_propose_and_vote():
    engine = ConsensusEngine()
    proposal = {"id": "p1", "action": "recover"}
    proposed = engine.propose(proposal, ["agent-a", "agent-b"])
    assert proposed.decision == "pending"
    assert proposed.participating_agents == ["agent-a", "agent-b"]

    v1 = engine.vote("p1", "agent-a", VoteChoice.APPROVE, 0.9)
    v2 = engine.vote("p1", "agent-b", VoteChoice.REJECT, 0.8)
    assert v1.vote == VoteChoice.APPROVE
    assert v2.vote == VoteChoice.REJECT


def test_consensus_engine_tally():
    engine = ConsensusEngine(threshold=0.6)
    engine.propose({"id": "q1", "action": "flash"}, ["a", "b", "c"])
    engine.vote("q1", "a", VoteChoice.APPROVE, 0.9)
    engine.vote("q1", "b", VoteChoice.APPROVE, 0.8)
    engine.vote("q1", "c", VoteChoice.REJECT, 0.7)
    result = engine.tally("q1")
    assert result.decision == "approved"
    assert result.confidence == pytest.approx(2 / 3)
    assert len(result.votes) == 3


def test_delegation_router_route():
    router = DelegationRouter()
    chosen = router.route({"task": "x"}, ["recovery_agent", "hw_agent"], {"cap": []})
    assert chosen == "recovery_agent"


def test_delegation_router_can_delegate():
    router = DelegationRouter()
    assert router.can_delegate("agent-a", "agent-b", {"task": "x"}) is True
    result = router.delegate("agent-a", "agent-b", {"task": "x"})
    assert result.success is True
    assert result.result["delegated_to"] == "agent-b"
