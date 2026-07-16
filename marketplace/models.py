"""
P10 Engineering Ecosystem — persistence model.

Marketplace submissions flow through an approval workflow with quality
gates and version policies. Approvals are recorded for audit.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text, Float

from core.database import Base


class MarketplaceApproval(Base):
    __tablename__ = "marketplace_approvals"

    id = Column(String, primary_key=True)
    submission_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    submitter = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending|approved|rejected
    reviewer = Column(String, nullable=True)
    quality_score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
