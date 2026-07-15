"""
P4 Engineering Intelligence — persistence models.

Generated suggestions carry a confidence score (gated before display)
and a human-approval flag. Acceptance/rejection feedback drives the
false-positive rate used as a P4 KPI.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text, Float, Boolean

from core.database import Base


class EngineeringReport(Base):
    __tablename__ = "engineering_reports"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0, nullable=False)
    approved = Column(Boolean, default=False, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending|displayed|executed|rejected
    details_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EngineeringFeedback(Base):
    __tablename__ = "engineering_feedback"

    id = Column(String, primary_key=True)
    report_id = Column(String, index=True, nullable=False)
    accepted = Column(Boolean, default=False, nullable=False)
    false_positive = Column(Boolean, default=False, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
