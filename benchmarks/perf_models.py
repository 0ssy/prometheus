"""
P6 High Performance Engine — persistence model.

Per-run inference performance: tokens/sec, latency, GPU memory
utilization. Used by the regression guard that fails CI when a run
regresses beyond the P6 threshold (default 3%).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Float

from core.database import Base


class PerfMetric(Base):
    __tablename__ = "perf_metrics"

    id = Column(String, primary_key=True)
    run_id = Column(String, index=True, nullable=False)
    model_tier = Column(String, index=True, nullable=False)
    tokens_per_sec = Column(Float, nullable=False)
    latency_ms = Column(Float, nullable=True)
    memory_utilization = Column(Float, nullable=True)  # 0..1
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
