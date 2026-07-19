"""
AI Speech capability (RC8 AI Runtime Expansion).

Exposes speech-to-text (transcribe) and text-to-speech (synthesize) over
raw audio bytes and text. The current implementation is a stub that
returns empty results; the interface is stable for a real speech backend.
"""

from __future__ import annotations

from core.logger import get_logger

logger = get_logger(__name__)


class SpeechEngine:
    def transcribe(self, audio_data: bytes, language: str = "en") -> dict:
        return {"text": "", "language": language, "status": "stub"}

    def synthesize(self, text: str, voice: str = "default") -> dict:
        return {
            "text": text,
            "voice": voice,
            "audio_format": "wav",
            "status": "stub",
        }
