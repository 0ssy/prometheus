"""
P6 High Performance Engine — regression guard.

Records a perf run and compares against the previous run for the same
model tier. A drop in tokens/sec greater than ``max_regression`` (3%)
fails the guard (CI blocks the merge).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger
from sqlalchemy.orm import Session

from benchmarks.perf_models import PerfMetric

logger = get_logger(__name__)

DEFAULT_MAX_REGRESSION = 0.03


@dataclass
class PerfRun:
    run_id: str
    model_tier: str
    tokens_per_sec: float
    latency_ms: float | None = None
    memory_utilization: float | None = None


class PerfRegistry:
    def __init__(self, max_regression: float = DEFAULT_MAX_REGRESSION):
        self._max_regression = max_regression

    def record(self, db: Session, run: PerfRun) -> PerfMetric:
        metric = PerfMetric(
            id=str(uuid.uuid4()),
            run_id=run.run_id,
            model_tier=run.model_tier,
            tokens_per_sec=run.tokens_per_sec,
            latency_ms=run.latency_ms,
            memory_utilization=run.memory_utilization,
            created_at=datetime.now(timezone.utc),
        )
        db.add(metric)
        db.commit()
        return metric

    def previous(self, db: Session, model_tier: str, before_id: str) -> PerfMetric | None:
        return (
            db.query(PerfMetric)
            .filter(PerfMetric.model_tier == model_tier, PerfMetric.id != before_id)
            .order_by(PerfMetric.created_at.desc())
            .first()
        )

    def check_regression(self, db: Session, metric: PerfMetric) -> dict[str, Any]:
        prev = self.previous(db, metric.model_tier, metric.id)
        if prev is None:
            return {"regression": False, "delta": 0.0, "previous": None}
        if prev.tokens_per_sec <= 0:
            return {"regression": False, "delta": 0.0, "previous": prev.tokens_per_sec}
        delta = (metric.tokens_per_sec - prev.tokens_per_sec) / prev.tokens_per_sec
        regression = delta < -self._max_regression
        if regression:
            logger.warning(
                "Perf regression on %s: %.2f%% (threshold %.2f%%)",
                metric.model_tier, delta * 100, -self._max_regression * 100,
            )
        return {
            "regression": regression,
            "delta": round(delta, 4),
            "previous": prev.tokens_per_sec,
        }
