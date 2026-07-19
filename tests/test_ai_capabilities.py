"""
Tests for the RC8 AI runtime capabilities (embeddings, memory
consolidation, vision, speech).

Validates that the capabilities register on the ``CapabilityApi`` surface
with the correct permissions and that they execute through the authorized
path the Rust Aether ``ToolDispatcher`` hits.
"""

from __future__ import annotations

import pytest

from core.capabilities import CapabilityManager
from services.ai_capabilities import register_ai_capabilities


@pytest.fixture()
def cap_api():
    manager = CapabilityManager()
    register_ai_capabilities(
        manager, memory_api=None, reasoning_api=None, db=None
    )
    return manager


def _names(cap_api) -> set[str]:
    return {c["name"] for c in cap_api.discover(prefix="ai.")}


def test_ai_capabilities_registered(cap_api) -> None:
    assert {
        "ai.embeddings.embed",
        "ai.embeddings.embed_batch",
        "ai.memory.consolidate",
        "ai.memory.promote",
        "ai.vision.ocr",
        "ai.vision.detect_objects",
        "ai.speech.transcribe",
        "ai.speech.synthesize",
    }.issubset(_names(cap_api))


def test_embed_executes(cap_api) -> None:
    result = cap_api.execute(
        "ai.embeddings.embed",
        payload={"text": "hello"},
        granted_permissions={"memory.write"},
    )
    assert result["text"] == "hello"
    assert result["dimensions"] == 384
    assert len(result["vector"]) == 384
    assert result["status"] == "stub"


def test_embed_batch_executes(cap_api) -> None:
    result = cap_api.execute(
        "ai.embeddings.embed_batch",
        payload={"texts": ["a", "b"]},
        granted_permissions={"memory.write"},
    )
    assert len(result) == 2
    assert result[0]["text"] == "a"


def test_memory_consolidate_executes(cap_api) -> None:
    result = cap_api.execute(
        "ai.memory.consolidate",
        payload={},
        granted_permissions={"memory.write"},
    )
    assert result == {"consolidated": 0, "status": "stub"}


def test_memory_promote_executes(cap_api) -> None:
    result = cap_api.execute(
        "ai.memory.promote",
        payload={"memory_id": "m1"},
        granted_permissions={"memory.write"},
    )
    assert result == {"memory_id": "m1", "status": "stub"}


def test_vision_ocr_executes(cap_api) -> None:
    result = cap_api.execute(
        "ai.vision.ocr",
        payload={"image_data": b""},
        granted_permissions={"device.read"},
    )
    assert result == {"text": "", "confidence": 0.0, "status": "stub"}


def test_vision_detect_objects_executes(cap_api) -> None:
    result = cap_api.execute(
        "ai.vision.detect_objects",
        payload={"image_data": b""},
        granted_permissions={"device.read"},
    )
    assert result == {"objects": [], "status": "stub"}


def test_speech_transcribe_executes(cap_api) -> None:
    result = cap_api.execute(
        "ai.speech.transcribe",
        payload={"audio_data": b"", "language": "fr"},
        granted_permissions={"device.read"},
    )
    assert result == {"text": "", "language": "fr", "status": "stub"}


def test_speech_synthesize_executes(cap_api) -> None:
    result = cap_api.execute(
        "ai.speech.synthesize",
        payload={"text": "hi"},
        granted_permissions={"device.read"},
    )
    assert result == {
        "text": "hi",
        "voice": "default",
        "audio_format": "wav",
        "status": "stub",
    }


def test_embed_denied_without_permission(cap_api) -> None:
    with pytest.raises(PermissionError):
        cap_api.execute(
            "ai.embeddings.embed",
            payload={"text": "hello"},
            granted_permissions=set(),
        )


def test_vision_denied_without_permission(cap_api) -> None:
    with pytest.raises(PermissionError):
        cap_api.execute(
            "ai.vision.ocr",
            payload={"image_data": b""},
            granted_permissions=set(),
        )
