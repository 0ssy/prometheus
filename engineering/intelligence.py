"""
P4 Engineering Intelligence — confidence gating, human approval, feedback.

A suggestion must exceed the confidence threshold before it is shown,
and critical actions require an explicit human approval flag. Feedback
records acceptance/rejection and false-positive labels used to compute
the P4 KPIs (acceptance rate, false-positive rate).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger
from sqlalchemy.orm import Session

from engineering.models import EngineeringReport, EngineeringFeedback

logger = get_logger(__name__)

DEFAULT_CONFIDENCE_THRESHOLD = 0.6


@dataclass
class Suggestion:
    title: str
    summary: str
    confidence: float
    details: dict[str, Any] = None


class EngineeringIntelligence:
    def __init__(self, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD):
        self._threshold = confidence_threshold

    def submit(self, db: Session, suggestion: Suggestion) -> EngineeringReport:
        report = EngineeringReport(
            id=str(uuid.uuid4()),
            title=suggestion.title,
            summary=suggestion.summary,
            confidence=suggestion.confidence,
            details_json=_dump(suggestion.details),
            # Gated: only displayed if confidence clears the threshold.
            status="displayed" if suggestion.confidence >= self._threshold else "pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(report)
        db.commit()
        return report

    def approve(self, db: Session, report_id: str) -> EngineeringReport:
        report = db.get(EngineeringReport, report_id)
        if report is None:
            raise ValueError(f"No such report: {report_id}")
        if report.confidence < self._threshold:
            raise PermissionError("Cannot approve below confidence threshold")
        report.approved = True
        report.status = "executed"
        db.commit()
        return report

    def reject(self, db: Session, report_id: str) -> EngineeringReport:
        report = db.get(EngineeringReport, report_id)
        if report is None:
            raise ValueError(f"No such report: {report_id}")
        report.status = "rejected"
        db.commit()
        return report

    def record_feedback(
        self,
        db: Session,
        report_id: str,
        accepted: bool,
        false_positive: bool = False,
        note: str | None = None,
    ) -> EngineeringFeedback:
        fb = EngineeringFeedback(
            id=str(uuid.uuid4()),
            report_id=report_id,
            accepted=accepted,
            false_positive=false_positive,
            note=note,
            created_at=datetime.now(timezone.utc),
        )
        db.add(fb)
        db.commit()
        return fb

    def metrics(self, db: Session) -> dict[str, float]:
        feedback = db.query(EngineeringFeedback).all()
        total = len(feedback)
        if total == 0:
            return {"acceptance_rate": 0.0, "false_positive_rate": 0.0, "sample_size": 0}
        accepted = sum(1 for f in feedback if f.accepted)
        fp = sum(1 for f in feedback if f.false_positive)
        return {
            "acceptance_rate": round(accepted / total, 4),
            "false_positive_rate": round(fp / total, 4),
            "sample_size": total,
        }


def _dump(details: dict[str, Any] | None) -> str:
    import json

    return json.dumps(details or {}, default=str)
