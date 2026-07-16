from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MemoryStats:
    total_mb: float
    used_mb: float
    cached_mb: float
    available_mb: float


class MemoryManager:
    def __init__(self) -> None:
        self._retention_policy: dict[str, Any] = {}

    def get_stats(self) -> MemoryStats:
        try:
            import psutil
            vm = psutil.virtual_memory()
            return MemoryStats(
                total_mb=vm.total / 1024 / 1024,
                used_mb=vm.used / 1024 / 1024,
                cached_mb=vm.cached / 1024 / 1024 if hasattr(vm, "cached") else 0.0,
                available_mb=vm.available / 1024 / 1024,
            )
        except ImportError:
            logger.warning("psutil not installed; returning zeroed memory stats")
            return MemoryStats(total_mb=0.0, used_mb=0.0, cached_mb=0.0, available_mb=0.0)

    def collect(self) -> int:
        import gc
        collected = gc.collect()
        return collected

    def get_leak_candidates(self) -> list[str]:
        return []

    def set_retention_policy(self, policy: dict[str, Any]) -> None:
        self._retention_policy = policy
