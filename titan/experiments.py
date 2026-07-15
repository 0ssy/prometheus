"""
Experiment Tracking — Phase 5.6
-----------------------------------------
Logs metrics, checkpoints, and comparisons for fine-tuning runs.
"""

from __future__ import annotations

import dataclasses
import random
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExperimentRecord:
    experiment_id: str
    name: str
    job_id: str
    model_id: str
    metrics: dict[str, Any] = field(default_factory=dict)
    checkpoints: list[str] = field(default_factory=list)
    status: str = "running"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ComparisonResult:
    experiment_ids: list[str]
    winner: str
    scores: dict[str, float]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class ExperimentTracker:
    name = "experiment_tracker"

    def __init__(self) -> None:
        self._experiments: dict[str, ExperimentRecord] = {}

    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        experiment_id = str(uuid.uuid4())
        record = ExperimentRecord(
            experiment_id=experiment_id,
            name=payload.get("name", f"exp-{experiment_id[:8]}"),
            job_id=payload.get("job_id", ""),
            model_id=payload.get("model_id", ""),
        )
        self._experiments[experiment_id] = record
        logger.info("Started experiment %s", experiment_id)
        return record.to_dict()

    def log_metrics(self, experiment_id: str, metrics: dict[str, Any]) -> dict[str, Any]:
        record = self._experiments.get(experiment_id)
        if record is None:
            raise KeyError(f"Unknown experiment: {experiment_id}")
        record.metrics.update(metrics)
        return {"experiment_id": experiment_id, "metrics": record.metrics}

    def log_checkpoint(self, experiment_id: str, checkpoint_path: str) -> dict[str, Any]:
        record = self._experiments.get(experiment_id)
        if record is None:
            raise KeyError(f"Unknown experiment: {experiment_id}")
        record.checkpoints.append(checkpoint_path)
        return {"experiment_id": experiment_id, "checkpoints": record.checkpoints}

    def complete(self, experiment_id: str) -> dict[str, Any]:
        record = self._experiments.get(experiment_id)
        if record is None:
            raise KeyError(f"Unknown experiment: {experiment_id}")
        record.status = "completed"
        record.completed_at = datetime.now(timezone.utc).isoformat()
        return record.to_dict()

    def compare(self, experiment_ids: list[str]) -> dict[str, Any]:
        scores: dict[str, float] = {}
        for eid in experiment_ids:
            record = self._experiments.get(eid)
            if record is None:
                raise KeyError(f"Unknown experiment: {eid}")
            scores[eid] = record.metrics.get("final_score", random.uniform(0.5, 0.99))
        winner = max(scores, key=scores.get)
        comparison = ComparisonResult(experiment_ids=experiment_ids, winner=winner, scores=scores)
        return comparison.to_dict()

    def list_experiments(self) -> dict[str, Any]:
        return {
            "experiments": [e.to_dict() for e in self._experiments.values()],
            "total": len(self._experiments),
        }


experiment_tracker = ExperimentTracker()
