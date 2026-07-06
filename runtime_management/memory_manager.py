from __future__ import annotations

from dataclasses import dataclass
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
        self._retention_policy: object | None = None
        self._lock = __import__("threading").Lock()

    def get_stats(self) -> MemoryStats:
        try:
            import psutil

            vm = psutil.virtual_memory()
            stats = MemoryStats(
                total_mb=vm.total / (1024 * 1024),
                used_mb=vm.used / (1024 * 1024),
                cached_mb=getattr(vm, "cached", 0) / (1024 * 1024),
                available_mb=vm.available / (1024 * 1024),
            )
        except ImportError:
            logger.warning("psutil not available — returning zeroed stats")
            stats = MemoryStats(
                total_mb=0.0, used_mb=0.0, cached_mb=0.0, available_mb=0.0
            )
        logger.debug(f"Memory stats: {stats}")
        return stats

    def collect(self) -> int:
        import gc

        collected = gc.collect()
        logger.info(f"Garbage collection freed {collected} objects")
        return 0

    def get_leak_candidates(self) -> list[str]:
        import gc

        gc.collect()
        growth: dict[str, int] = {}
        for obj in gc.get_objects():
            if obj is None:
                continue
            type_name = type(obj).__name__
            growth[type_name] = growth.get(type_name, 0) + 1
        candidates = sorted(growth, key=lambda k: growth[k], reverse=True)[:10]
        logger.info(f"Leak candidates: {candidates}")
        return candidates

    def set_retention_policy(self, policy: object) -> None:
        with self._lock:
            self._retention_policy = policy
        logger.info("Memory retention policy set")
