"""
P5 Titan AI Platform — persistence models.

Datasets carry license + lineage + hash for governance. Models record
eval scores, license, artifact path, and a reproducibility hash of
(dataset + code + config).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text

from core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String, primary_key=True)
    name = Column(String, index=True, nullable=False)
    license = Column(String, nullable=False)
    source_hash = Column(String, nullable=False)
    lineage_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Model(Base):
    __tablename__ = "models"

    id = Column(String, primary_key=True)
    name = Column(String, index=True, nullable=False)
    version = Column(String, nullable=False)
    dataset_id = Column(String, index=True, nullable=True)
    license = Column(String, nullable=True)
    eval_scores_json = Column(Text, default="{}")
    artifact_path = Column(String, nullable=True)
    reproducibility_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
