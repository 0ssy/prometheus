"""
AI Embeddings capability (RC8 AI Runtime Expansion).

Turns text into dense vectors so the memory and reasoning subsystems can
perform semantic lookups. The current implementation is a deterministic
stub that returns fixed-dimension zero vectors; the interface is stable so
a real model backend can be dropped in without touching callers.
"""

from __future__ import annotations

from core.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_DIMENSIONS = 384


class EmbeddingEngine:
    def embed(self, text: str, model: str = "default") -> dict:
        return {
            "text": text,
            "model": model,
            "dimensions": _DEFAULT_DIMENSIONS,
            "vector": [0.0] * _DEFAULT_DIMENSIONS,
            "status": "stub",
        }

    def embed_batch(self, texts: list[str], model: str = "default") -> list[dict]:
        return [self.embed(text, model=model) for text in texts]
