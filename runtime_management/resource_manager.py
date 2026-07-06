from __future__ import annotations

from dataclasses import dataclass
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
    max_cpu_percent: float
    max_memory_mb: float
    max_disk_mb: float
    max_connections: int


class ResourceManager:
    def __init__(self) -> None:
        self._limits = ResourceLimits(
            max_cpu_percent=100.0,
            max_memory_mb=8192.0,
            max_disk_mb=102400.0,
            max_connections=1000,
        )
        self._throttled = False
        self._throttle_reason: str | None = None
        self._lock = __import__("threading").Lock()

    def get_usage(self) -> ResourceUsage:
        try:
            import psutil

            cpu = psutil.cpu_percent()
            vm = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            net = psutil.net_io_counters()
            usage = ResourceUsage(
                cpu_percent=cpu,
                memory_mb=vm.used / (1024 * 1024),
                disk_mb=disk.used / (1024 * 1024),
                network_mbps=(net.bytes_sent + net.bytes_recv) / (1024 * 1024),
                active_connections=len(psutil.net_connections()),
            )
        except ImportError:
            logger.warning("psutil not available — returning zeroed usage")
            usage = ResourceUsage(
                cpu_percent=0.0,
                memory_mb=0.0,
                disk_mb=0.0,
                network_mbps=0.0,
                active_connections=0,
            )
        logger.debug(f"Resource usage: {usage}")
        return usage

    def check_limits(self, limits: ResourceLimits) -> dict:
        usage = self.get_usage()
        violations: list[str] = []
        if usage.cpu_percent > limits.max_cpu_percent:
            violations.append("cpu")
        if usage.memory_mb > limits.max_memory_mb:
            violations.append("memory")
        if usage.disk_mb > limits.max_disk_mb:
            violations.append("disk")
        if usage.active_connections > limits.max_connections:
            violations.append("connections")
        result = {"within_limits": not violations, "violations": violations}
        logger.info(f"Limit check: {result}")
        return result

    def set_limits(self, limits: ResourceLimits) -> None:
        with self._lock:
            self._limits = limits
        logger.info(f"Resource limits set: {limits}")

    def throttle(self, reason: str) -> None:
        with self._lock:
            self._throttled = True
            self._throttle_reason = reason
        logger.warning(f"Resource throttling engaged: {reason}")

    def release(self) -> None:
        with self._lock:
            self._throttled = False
            self._throttle_reason = None
        logger.info("Resource throttling released")
