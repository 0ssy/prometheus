from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ResourceUsage:
    cpu_percent: float
    memory_mb: float
    disk_mb: float
    network_mbps: float
    active_connections: int


@dataclass
class ResourceLimits:
    max_cpu_percent: float = 90.0
    max_memory_mb: float = 4096.0
    max_disk_mb: float = 10240.0
    max_connections: int = 1000


class ResourceManager:
    def __init__(self) -> None:
        self._limits: ResourceLimits | None = None
        self._throttled: bool = False
        self._throttle_reason: str | None = None

    def get_usage(self) -> ResourceUsage:
        try:
            import psutil
            return ResourceUsage(
                cpu_percent=psutil.cpu_percent(),
                memory_mb=psutil.virtual_memory().used / 1024 / 1024,
                disk_mb=psutil.disk_usage("/").used / 1024 / 1024,
                network_mbps=0.0,
                active_connections=len(psutil.net_connections()),
            )
        except ImportError:
            logger.warning("psutil not installed; returning zeroed resource usage")
            return ResourceUsage(cpu_percent=0.0, memory_mb=0.0, disk_mb=0.0, network_mbps=0.0, active_connections=0)

    def check_limits(self, limits: ResourceLimits) -> dict[str, Any]:
        usage = self.get_usage()
        violations = []
        if usage.cpu_percent > limits.max_cpu_percent:
            violations.append(f"CPU {usage.cpu_percent}% > {limits.max_cpu_percent}%")
        if usage.memory_mb > limits.max_memory_mb:
            violations.append(f"Memory {usage.memory_mb}MB > {limits.max_memory_mb}MB")
        if usage.active_connections > limits.max_connections:
            violations.append(f"Connections {usage.active_connections} > {limits.max_connections}")
        return {"within_limits": len(violations) == 0, "violations": violations}

    def set_limits(self, limits: ResourceLimits) -> None:
        self._limits = limits

    def throttle(self, reason: str) -> None:
        logger.warning("Throttling requested: %s", reason)

    def release(self) -> None:
        self._limits = None
        self._throttled = False
        self._throttle_reason = None

    def to_dict(self) -> dict[str, Any]:
        usage = self.get_usage()
        return {
            "cpu_percent": usage.cpu_percent,
            "memory_mb": usage.memory_mb,
            "disk_mb": usage.disk_mb,
            "network_mbps": usage.network_mbps,
            "active_connections": usage.active_connections,
            "limits": {
                "max_cpu_percent": self._limits.max_cpu_percent if self._limits else 90.0,
                "max_memory_mb": self._limits.max_memory_mb if self._limits else 4096.0,
                "max_disk_mb": self._limits.max_disk_mb if self._limits else 10240.0,
                "max_connections": self._limits.max_connections if self._limits else 1000,
            },
            "throttled": self._throttled,
            "throttle_reason": self._throttle_reason,
        }
