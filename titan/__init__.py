"""
Titan AI Platform
-----------------------------------------
Training, fine-tuning, evaluation, and model registry for Prometheus.

Titan runs *after* inference (Aether). It owns the full model lifecycle:
dataset preparation, tokenization, fine-tuning, evaluation, quantization,
registry, and experiment tracking.
"""

from __future__ import annotations

from core.logger import get_logger

logger = get_logger(__name__)
