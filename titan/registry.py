"""
Model Registry — Phase 5.5
-----------------------------------------
Registers, versions, tags, and deploys fine-tuned models.

Titan registers completed models as new Aether providers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ModelRecord:
    model_id: str
    name: str
    base_model: str
    version: str
    tags: list[str] = field(default_factory=list)
    status: str = "registered"
    provider_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class ModelRegistry:
    name = "model_registry"

    def __init__(self) -> None:
        self._models: dict[str, ModelRecord] = {}

    def register(self, payload: dict[str, Any]) -> dict[str, Any]:
        model_id = str(uuid.uuid4())
        record = ModelRecord(
            model_id=model_id,
            name=payload.get("name", f"model-{model_id[:8]}"),
            base_model=payload.get("base_model", "unknown"),
            version=payload.get("version", "v1.0.0"),
            tags=list(payload.get("tags", [])),
            metadata=dict(payload.get("metadata", {})),
        )
        self._models[model_id] = record
        logger.info("Registered model %s (%s)", model_id, record.name)
        return record.to_dict()

    def get(self, model_id: str) -> dict[str, Any]:
        record = self._models.get(model_id)
        if record is None:
            raise KeyError(f"Unknown model: {model_id}")
        return record.to_dict()

    def list_models(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        tag = (payload or {}).get("tag")
        models = list(self._models.values())
        if tag:
            models = [m for m in models if tag in m.tags]
        return {"models": [m.to_dict() for m in models], "total": len(models)}

    def version(self, model_id: str, new_version: str) -> dict[str, Any]:
        record = self._models.get(model_id)
        if record is None:
            raise KeyError(f"Unknown model: {model_id}")
        record.version = new_version
        logger.info("Versioned %s to %s", model_id, new_version)
        return record.to_dict()

    def tag(self, model_id: str, tags: list[str]) -> dict[str, Any]:
        record = self._models.get(model_id)
        if record is None:
            raise KeyError(f"Unknown model: {model_id}")
        for tag in tags:
            if tag not in record.tags:
                record.tags.append(tag)
        return record.to_dict()

    def deploy(self, model_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = self._models.get(model_id)
        if record is None:
            raise KeyError(f"Unknown model: {model_id}")
        record.status = "deployed"
        record.provider_id = payload.get("provider_id", f"titan-{model_id[:8]}")
        logger.info("Deployed model %s as provider %s", model_id, record.provider_id)
        return {
            "model_id": model_id,
            "status": "deployed",
            "provider_id": record.provider_id,
            "endpoint": "/v1/chat/completions",
        }

    def register_as_provider(self, model_id: str) -> dict[str, Any]:
        record = self._models.get(model_id)
        if record is None:
            raise KeyError(f"Unknown model: {model_id}")
        record.status = "registered_as_provider"
        record.provider_id = f"titan-{model_id[:8]}"
        logger.info("Registered model %s as Aether provider %s", model_id, record.provider_id)
        return record.to_dict()


model_registry = ModelRegistry()
