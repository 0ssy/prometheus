from __future__ import annotations

import pytest

from agents import AgentCoordinator, ConsensusEngine, DelegationRouter, TaskPlanner
from agents.coordinator import TaskStatus
from agents.consensus import VoteChoice


def test_agent_coordinator_create_task():
    coordinator = AgentCoordinator()
    result = coordinator.coordinate(
        [{"task_id": "t1", "description": "do thing", "required_capabilities": ["cap"], "priority": 3}]
    )
    assert result["count"] == 1
    assert len(result["submitted"]) == 1
    assert result["results"] == {}
    task = coordinator.get_task(result["submitted"][0])
    assert task is not None
    assert task.description == "do thing"
    assert task.required_capabilities == {"cap"}
    assert task.priority == 3
    assert task.status == TaskStatus.PENDING


def test_agent_coordinator_coordinate():
    coordinator = AgentCoordinator()
    result = coordinator.coordinate(
        [
            {"task_id": "a", "description": "first"},
            {"task_id": "b", "description": "second", "assigned_agent": "agent-x"},
        ]
    )
    assert result["count"] == 2
    assert len(result["submitted"]) == 2
    assert len(result["results"]) == 1


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

    v1 = engine.vote(proposed.proposal_id, "agent-a", VoteChoice.APPROVE, 0.9, "looks good")
    v2 = engine.vote(proposed.proposal_id, "agent-b", VoteChoice.REJECT, 0.8, "needs work")
    assert v1.vote == VoteChoice.APPROVE
    assert v2.vote == VoteChoice.REJECT


def test_consensus_engine_tally():
    engine = ConsensusEngine(threshold=0.6)
    proposed = engine.propose({"id": "q1", "action": "flash"}, ["a", "b", "c"])
    engine.vote(proposed.proposal_id, "a", VoteChoice.APPROVE, 0.9, "approve")
    engine.vote(proposed.proposal_id, "b", VoteChoice.APPROVE, 0.8, "approve")
    engine.vote(proposed.proposal_id, "c", VoteChoice.REJECT, 0.7, "reject")
    result = engine.tally(proposed.proposal_id)
    assert result.decision == "approved"
    assert result.confidence > 0.0
    assert len(result.votes) == 3


def test_delegation_router_route():
    router = DelegationRouter()
    chosen = router.route(
        "recover",
        ["recovery_agent", "hw_agent"],
        {"recover": ["device.recover"], "recovery_agent": ["device.recover"], "hw_agent": []},
    )
    assert chosen == "recovery_agent"


def test_delegation_router_can_delegate():
    router = DelegationRouter()
    assert router.can_delegate("agent-a", "agent-b", "recover") is True
    result = router.delegate("agent-a", "agent-b", "recover")
    assert result.success is True
    assert result.result["to"] == "agent-b"
