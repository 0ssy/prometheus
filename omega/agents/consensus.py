from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class VoteChoice(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class Vote:
    agent_name: str
    vote: VoteChoice
    confidence: float
    reasoning: str = ""


@dataclass
class ConsensusResult:
    decision: str
    votes: list[Vote]
    confidence: float
    participating_agents: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "votes": [v.__dict__ for v in self.votes],
            "confidence": self.confidence,
            "participating_agents": self.participating_agents,
        }


class ConsensusEngine:
    def __init__(self, threshold: float = 0.6) -> None:
        self._threshold = threshold
        self._votes: dict[str, list[Vote]] = {}
        self._lock = threading.RLock()

    def propose(self, proposal: dict, participants: list[str]) -> ConsensusResult:
        proposal_id = proposal.get("id", str(uuid.uuid4()))
        with self._lock:
            self._votes[proposal_id] = []
        return ConsensusResult(
            decision="pending",
            votes=[],
            confidence=0.0,
            participating_agents=participants,
        )

    def vote(self, proposal_id: str, agent_name: str, vote: VoteChoice, confidence: float, reasoning: str = "") -> Vote:
        v = Vote(agent_name=agent_name, vote=vote, confidence=confidence, reasoning=reasoning)
        with self._lock:
            self._votes.setdefault(proposal_id, []).append(v)
        return v

    def tally(self, proposal_id: str) -> ConsensusResult:
        with self._lock:
            votes = list(self._votes.get(proposal_id, []))
        if not votes:
            return ConsensusResult(decision="pending", votes=[], confidence=0.0, participating_agents=[])
        approve = sum(1 for v in votes if v.vote == VoteChoice.APPROVE)
        total = len(votes)
        confidence = approve / total if total > 0 else 0.0
        decision = "approved" if confidence >= self._threshold else "rejected"
        return ConsensusResult(
            decision=decision,
            votes=votes,
            confidence=confidence,
            participating_agents=[v.agent_name for v in votes],
        )

    def requires_consensus(self, action: str) -> bool:
        return action in ("recover", "flash", "reboot")

import threading
import uuid
