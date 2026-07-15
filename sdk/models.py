"""
P9 Prometheus SDK — persistence model.

Tracks published SDK versions per language and their compatibility
targets. Used by the certification/compatibility matrix.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime

from core.database import Base


class SdkVersion(Base):
    __tablename__ = "sdk_versions"

    id = Column(String, primary_key=True)
    language = Column(String, index=True, nullable=False)  # rust|python|typescript|cpp
    version = Column(String, nullable=False)
    compatibility_target = Column(String, nullable=False)  # semver floor
    published_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
