"""
AI capability registry (RC8 AI Runtime Expansion).

Registers the RC8 AI runtime capabilities on the ``CapabilityApi`` surface
so the Rust Aether ``ToolDispatcher`` (which POSTs to
``/capabilities/execute``) can invoke embeddings, memory consolidation,
vision, and speech through the same authorized path as hardware.

Each capability delegates to the engines in ``ai/`` and carries the exact
permission set the ``Authorizer`` requires, so nothing executes without
authorization (Phase 1 hardening boundary).
"""

from __future__ import annotations

from typing import Any

from ai.embeddings import EmbeddingEngine
from ai.memory_consolidation import MemoryConsolidator
from ai.speech import SpeechEngine
from ai.vision import VisionEngine
from core.logger import get_logger

logger = get_logger(__name__)

# Capability name -> permissions required (mirrors security/permissions.py action map).
_AI_CAPABILITIES: dict[str, set[str]] = {
    "ai.embeddings.embed": {"memory.write"},
    "ai.embeddings.embed_batch": {"memory.write"},
    "ai.memory.consolidate": {"memory.write"},
    "ai.memory.promote": {"memory.write"},
    "ai.vision.ocr": {"device.read"},
    "ai.vision.detect_objects": {"device.read"},
    "ai.speech.transcribe": {"device.read"},
    "ai.speech.synthesize": {"device.read"},
}


def register_ai_capabilities(
    cap_api, memory_api, reasoning_api, db
) -> None:
    """Register the RC8 AI runtime capabilities, delegating to the ai/ engines."""
    embeddings = EmbeddingEngine()
    consolidator = MemoryConsolidator()
    vision = VisionEngine()
    speech = SpeechEngine()

    def embed(payload: dict[str, Any]) -> dict[str, Any]:
        return embeddings.embed(
            payload["text"], model=payload.get("model", "default")
        )

    def embed_batch(payload: dict[str, Any]) -> list[dict[str, Any]]:
        return embeddings.embed_batch(
            payload["texts"], model=payload.get("model", "default")
        )

    def consolidate(payload: dict[str, Any]) -> dict[str, Any]:
        return consolidator.consolidate(memory_api, reasoning_api, db)

    def promote(payload: dict[str, Any]) -> dict[str, Any]:
        return consolidator.promote_to_long_term(
            payload["memory_id"], reasoning_api, db
        )

    def ocr(payload: dict[str, Any]) -> dict[str, Any]:
        return vision.ocr(payload.get("image_data", b""))

    def detect_objects(payload: dict[str, Any]) -> dict[str, Any]:
        return vision.detect_objects(payload.get("image_data", b""))

    def transcribe(payload: dict[str, Any]) -> dict[str, Any]:
        return speech.transcribe(
            payload.get("audio_data", b""), language=payload.get("language", "en")
        )

    def synthesize(payload: dict[str, Any]) -> dict[str, Any]:
        return speech.synthesize(
            payload["text"], voice=payload.get("voice", "default")
        )

    executors = {
        "ai.embeddings.embed": embed,
        "ai.embeddings.embed_batch": embed_batch,
        "ai.memory.consolidate": consolidate,
        "ai.memory.promote": promote,
        "ai.vision.ocr": ocr,
        "ai.vision.detect_objects": detect_objects,
        "ai.speech.transcribe": transcribe,
        "ai.speech.synthesize": synthesize,
    }

    target = "ai"
    for name, executor in executors.items():
        if cap_api.exists(name):
            continue
        cap_api.register(
            name=name,
            target=target,
            description=f"AI capability: {name}",
            permissions=set(_AI_CAPABILITIES[name]),
            executor=executor,
        )
    logger.info("Registered %d AI runtime capabilities", len(executors))
