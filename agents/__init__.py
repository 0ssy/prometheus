"""
Prometheus Multi-Agent Coordination Package — Phase Omega (Olympus) Sprint O2
--------------------------------------------------------------------------------
Coordination primitives for orchestrating work across multiple agents:
task coordination, planning/DAG scheduling, consensus voting, and delegation.
"""

from .coordinator import AgentCoordinator, AgentTask, TaskStatus
from .planner import TaskGraph, TaskNode, TaskPlanner
from .consensus import ConsensusEngine, ConsensusResult, Vote, VoteChoice
from .delegation import DelegationRequest, DelegationResult, DelegationRouter

__all__ = [
    "AgentCoordinator",
    "AgentTask",
    "TaskStatus",
    "TaskGraph",
    "TaskNode",
    "TaskPlanner",
    "ConsensusEngine",
    "ConsensusResult",
    "Vote",
    "VoteChoice",
    "DelegationRequest",
    "DelegationResult",
    "DelegationRouter",
]
