"""
P10 Engineering Ecosystem — marketplace governance.

Submissions are reviewed against a quality gate (minimum quality score)
and an approval/deny decision is recorded. Approved extensions become
installable; rejected ones are blocked.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from core.logger import get_logger
from sqlalchemy.orm import Session

from marketplace.models import MarketplaceApproval

logger = get_logger(__name__)

DEFAULT_QUALITY_GATE = 0.7


@dataclass
class Submission:
    submission_id: str
    name: str
    category: str
    submitter: str


class MarketplaceGovernance:
    def __init__(self, quality_gate: float = DEFAULT_QUALITY_GATE):
        self._quality_gate = quality_gate

    def submit(self, db: Session, sub: Submission) -> MarketplaceApproval:
        rec = MarketplaceApproval(
            id=str(uuid.uuid4()),
            submission_id=sub.submission_id,
            name=sub.name,
            category=sub.category,
            submitter=sub.submitter,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(rec)
        db.commit()
        return rec

    def pending(self, db: Session) -> list[MarketplaceApproval]:
        return db.query(MarketplaceApproval).filter(MarketplaceApproval.status == "pending").all()

    def review(
        self,
        db: Session,
        approval_id: str,
        decision: str,  # approved|rejected
        reviewer: str,
        quality_score: float,
        notes: str | None = None,
    ) -> MarketplaceApproval:
        rec = db.get(MarketplaceApproval, approval_id)
        if rec is None:
            raise ValueError(f"No such submission: {approval_id}")
        if rec.status != "pending":
            raise ValueError(f"Submission already reviewed: {rec.status}")
        if decision == "approved" and quality_score < self._quality_gate:
            raise PermissionError(
                f"Quality score {quality_score} below gate {self._quality_gate}; cannot approve"
            )
        rec.status = decision
        rec.reviewer = reviewer
        rec.quality_score = quality_score
        rec.notes = notes
        db.commit()
        return rec

    def approval_rate(self, db: Session) -> float:
        all_ = db.query(MarketplaceApproval).all()
        if not all_:
            return 0.0
        approved = sum(1 for a in all_ if a.status == "approved")
        return round(approved / len(all_), 4)
