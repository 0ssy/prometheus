"""
AI Vision capability (RC8 AI Runtime Expansion).

Exposes OCR and object detection over raw image bytes so agents can reason
about visual device output. The current implementation is a stub that
returns empty results; the interface is stable for a real vision backend.
"""

from __future__ import annotations

from core.logger import get_logger

logger = get_logger(__name__)


class VisionEngine:
    def ocr(self, image_data: bytes) -> dict:
        return {"text": "", "confidence": 0.0, "status": "stub"}

    def detect_objects(self, image_data: bytes) -> dict:
        return {"objects": [], "status": "stub"}
