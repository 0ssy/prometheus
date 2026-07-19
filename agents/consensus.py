"""
Prometheus Multi-Agent Coordination — Consensus
-------------------------------------------------
A threshold-based voting engine for collective decisions that require
agreement across participating agents. Proposals are tallied on demand.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class VoteChoice(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class Vote:
    agent_name: str
    vote: VoteChoice
    confidence: float
    reasoning: str
    proposal_id: str = ""


@dataclass
class ConsensusResult:
    proposal_id: str = ""
    decision: str = ""
    votes: list[Vote] = field(default_factory=list)
    confidence: float = 0.0
    participating_agents: list[str] = field(default_factory=list)


_CONSENSUS_REQUIRED_ACTIONS = {
    "deploy",
    "shutdown",
    "reconfigure",
    "override_safety",
    "reset_system",
}


class ConsensusEngine:
    def __init__(self, threshold: float = 0.6) -> None:
        self._threshold = threshold
        self._proposals: dict[str, dict[str, Any]] = {}
        self._votes: dict[str, list[Vote]] = {}
        self._counter = 0
        self._lock = threading.RLock()

    def propose(self, proposal: dict[str, Any], participants: list[str]) -> ConsensusResult:
        with self._lock:
            self._counter += 1
            proposal_id = f"prop-{self._counter:04d}"
            self._proposals[proposal_id] = {
                "proposal": proposal,
                "participants": list(participants),
            }
            self._votes[proposal_id] = []
        logger.info(f"Proposed {proposal_id} to {len(participants)} participants")
        return ConsensusResult(
            proposal_id=proposal_id,
            decision="pending",
            votes=[],
            confidence=0.0,
            participating_agents=list(participants),
        )

    def vote(
        self,
        proposal_id: str,
        agent_name: str,
        vote: VoteChoice | str,
        confidence: float,
        reasoning: str,
    ) -> Vote:
        if isinstance(vote, str):
            vote = VoteChoice(vote)
        with self._lock:
            if proposal_id not in self._proposals:
                raise KeyError(f"No such proposal: {proposal_id}")
            v = Vote(
                agent_name=agent_name,
                vote=vote,
                confidence=float(confidence),
                reasoning=reasoning,
                proposal_id=proposal_id,
            )
            # One vote per agent — replace any prior vote.
            self._votes[proposal_id] = [
                existing for existing in self._votes[proposal_id]
                if existing.agent_name != agent_name
            ]
            self._votes[proposal_id].append(v)
        logger.info(f"Agent '{agent_name}' voted {vote.value} on {proposal_id}")
        return v

    def tally(self, proposal_id: str) -> ConsensusResult:
        with self._lock:
            if proposal_id not in self._proposals:
                raise KeyError(f"No such proposal: {proposal_id}")
            participants = list(self._proposals[proposal_id]["participants"])
            votes = list(self._votes[proposal_id])
        if not participants:
            return ConsensusResult(
                proposal_id=proposal_id,
                decision="no_participants",
                votes=votes,
                confidence=0.0,
                participating_agents=[],
            )
        deciding = [v for v in votes if v.vote != VoteChoice.ABSTAIN]
        voted_agents = {v.agent_name for v in votes}
        if len(voted_agents) < len(participants):
            decision = "pending"
            confidence = 0.0
        else:
            approve = [v for v in deciding if v.vote == VoteChoice.APPROVE]
            if deciding:
                approve_conf = sum(v.confidence for v in approve) / len(deciding)
                ratio = len(approve) / len(deciding)
            else:
                approve_conf = 0.0
                ratio = 0.0
            confidence = round(approve_conf * ratio, 4)
            decision = "approved" if ratio >= self._threshold else "rejected"
        return ConsensusResult(
            proposal_id=proposal_id,
            decision=decision,
            votes=votes,
            confidence=confidence,
            participating_agents=participants,
        )

    def requires_consensus(self, action: str) -> bool:
        return action in _CONSENSUS_REQUIRED_ACTIONS
