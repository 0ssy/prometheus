"""
P11 Prometheus OS — persistence model.

Tracks end-to-end enterprise workflows (device connect -> firmware
inspect -> simulation -> AI-assisted recovery -> deployment) so the
final integration success rate is measurable and auditable.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text, Boolean

from core.database import Base


class EnterpriseWorkflow(Base):
    __tablename__ = "enterprise_workflows"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    device_id = Column(String, index=True, nullable=True)
    steps_json = Column(Text, default="[]")
    success = Column(Boolean, default=False, nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
