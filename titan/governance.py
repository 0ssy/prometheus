"""
P5 Titan AI Platform — data governance / license scanning.

Unapproved dataset licenses are blocked at upload; model reproducibility
is captured as a hash of (dataset + code + config) so runs can be
verified across the P5 reproducibility gate.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger
from sqlalchemy.orm import Session

from titan.models import Dataset, Model

logger = get_logger(__name__)

# Licenses permitted for training data under governance policy.
APPROVED_LICENSES = {
    "mit",
    "apache-2.0",
    "bsd-3-clause",
    "cc-by-4.0",
    "cc0-1.0",
    "public-domain",
    "permissive",
}


class LicenseError(ValueError):
    pass


def scan_license(license: str) -> bool:
    return license.strip().lower() in APPROVED_LICENSES


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TitanGovernance:
    def register_dataset(
        self,
        db: Session,
        name: str,
        license: str,
        source_text: str,
        lineage: dict[str, Any] | None = None,
    ) -> Dataset:
        if not scan_license(license):
            raise LicenseError(f"Unapproved dataset license blocked: {license}")
        ds = Dataset(
            id=str(uuid.uuid4()),
            name=name,
            license=license.strip().lower(),
            source_hash=_hash(source_text),
            lineage_json=json.dumps(lineage or {}, default=str),
            created_at=datetime.now(timezone.utc),
        )
        db.add(ds)
        db.commit()
        return ds

    def register_model(
        self,
        db: Session,
        name: str,
        version: str,
        dataset_id: str | None,
        eval_scores: dict[str, Any],
        artifact_path: str | None,
        dataset_hash: str,
        code_hash: str,
        config: dict[str, Any],
    ) -> Model:
        rep_hash = _hash(json.dumps(
            {"dataset": dataset_hash, "code": code_hash, "config": config}, sort_keys=True
        ))
        model = Model(
            id=str(uuid.uuid4()),
            name=name,
            version=version,
            dataset_id=dataset_id,
            license=None,
            eval_scores_json=json.dumps(eval_scores, default=str),
            artifact_path=artifact_path,
            reproducibility_hash=rep_hash,
            created_at=datetime.now(timezone.utc),
        )
        db.add(model)
        db.commit()
        return model

    def verify_reproducibility(
        self,
        db: Session,
        model_id: str,
        dataset_hash: str,
        code_hash: str,
        config: dict[str, Any],
    ) -> bool:
        model = db.get(Model, model_id)
        if model is None or model.reproducibility_hash is None:
            return False
        expected = _hash(json.dumps(
            {"dataset": dataset_hash, "code": code_hash, "config": config}, sort_keys=True
        ))
        return model.reproducibility_hash == expected
