"""
Dataset Builder — Phase 5.1
-----------------------------------------
Prepares datasets for fine-tuning through a four-stage pipeline:
  prepare -> clean -> validate -> augment
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DatasetBuildResult:
    dataset_id: str
    name: str
    format: str
    total_records: int
    clean_records: int
    valid_records: int
    augmented_records: int
    source_path: str
    checksum: str
    status: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DatasetSummary:
    dataset_id: str
    name: str
    format: str
    total_records: int
    status: str
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


class DatasetBuilder:
    name = "dataset_builder"

    def prepare(self, source_path: str, name: str, format_hint: str = "jsonl") -> dict:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source_path}")

        fmt = format_hint if source.suffix else "jsonl"
        records = self._load_source(source, fmt)
        dataset_id = str(uuid.uuid4())
        checksum = hashlib.sha256(source.read_bytes()).hexdigest()[:16]

        logger.info("Prepared dataset %s from %s (%d records)", dataset_id, source_path, len(records))

        return DatasetBuildResult(
            dataset_id=dataset_id,
            name=name,
            format=fmt,
            total_records=len(records),
            clean_records=0,
            valid_records=0,
            augmented_records=0,
            source_path=str(source),
            checksum=checksum,
            status="prepared",
        ).to_dict()

    def build_pipeline(self, dataset_id: str, steps: list[str], payload: dict[str, Any]) -> dict:
        records = payload.get("records", [])
        fmt = payload.get("format", "jsonl")
        results: dict[str, Any] = {"dataset_id": dataset_id, "steps": {}}

        if "clean" in steps:
            records, clean_stats = self._clean(records)
            results["steps"]["clean"] = clean_stats
        if "validate" in steps:
            records, valid_stats = self._validate(records)
            results["steps"]["validate"] = valid_stats
        if "augment" in steps:
            records, aug_stats = self._augment(records)
            results["steps"]["augment"] = aug_stats

        results["final_records"] = len(records)
        results["format"] = fmt
        return results

    def get(self, dataset_id: str) -> dict:
        return DatasetSummary(
            dataset_id=dataset_id,
            name="dataset",
            format="jsonl",
            total_records=0,
            status="registered",
            created_at="2026-07-15T00:00:00Z",
        ).to_dict()

    def _load_source(self, path: Path, fmt: str) -> list[dict[str, Any]]:
        text = path.read_text(encoding="utf-8")
        if fmt == "jsonl":
            records = []
            for line in text.splitlines():
                line = line.strip()
                if line:
                    records.append(json.loads(line))
            return records
        if fmt == "json":
            data = json.loads(text)
            if isinstance(data, list):
                return data
            return [data]
        return [{"raw": text}]

    def _clean(self, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        cleaned = []
        removed = 0
        for r in records:
            if not any(v is None or (isinstance(v, str) and not v.strip()) for v in r.values()):
                cleaned.append(r)
            else:
                removed += 1
        return cleaned, {"removed": removed, "kept": len(cleaned)}

    def _validate(self, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        valid = []
        invalid_keys = 0
        for r in records:
            if "prompt" in r and "completion" in r:
                valid.append(r)
            else:
                invalid_keys += 1
        return valid, {"invalid": invalid_keys, "valid": len(valid)}

    def _augment(self, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        augmented = list(records)
        original_count = len(records)
        for r in records:
            if random.random() < 0.3:
                aug = dict(r)
                aug["prompt"] = r.get("prompt", "") + " [paraphrased]"
                augmented.append(aug)
        return augmented, {"added": len(augmented) - original_count, "total": len(augmented)}


dataset_builder = DatasetBuilder()
