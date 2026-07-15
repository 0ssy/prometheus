"""
P7 Distributed Computing — persistence models.

The control plane mirrors task state into ``distributed_tasks`` for
observability, and logs recovery events in ``distributed_recoveries``.
(Control plane/workers are Rust+Go services; this is the Python client
side, with a local fallback when the cluster is unavailable.)
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text

from core.database import Base


class DistributedTask(Base):
    __tablename__ = "distributed_tasks"

    id = Column(String, primary_key=True)
    node_id = Column(String, index=True, nullable=True)
    payload_json = Column(Text, default="{}")
    status = Column(String, default="queued", nullable=False)  # queued|running|done|failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DistributedRecovery(Base):
    __tablename__ = "distributed_recoveries"

    id = Column(String, primary_key=True)
    task_id = Column(String, index=True, nullable=True)
    node_id = Column(String, index=True, nullable=True)
    reason = Column(Text, nullable=True)
    recovered = Column(String, default="false", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
