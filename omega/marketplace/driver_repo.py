from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DriverPackage:
    name: str
    version: str
    transport: str
    supported_devices: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    checksum: str = ""


class DriverRepository:
    def __init__(self) -> None:
        self._drivers: dict[str, DriverPackage] = {}
        self._lock = threading.RLock()

    def register(self, driver: DriverPackage) -> str:
        driver_id = f"{driver.name}@{driver.version}"
        with self._lock:
            self._drivers[driver_id] = driver
            logger.info("Registered driver: %s", driver_id)
        return driver_id

    def discover(self, transport: str | None = None) -> list[DriverPackage]:
        with self._lock:
            results = list(self._drivers.values())
            if transport:
                results = [d for d in results if d.transport == transport]
            return results

    def get(self, name: str) -> DriverPackage | None:
        with self._lock:
            for driver in self._drivers.values():
                if driver.name == name:
                    return driver
            return None

    def list_by_transport(self, transport: str) -> list[DriverPackage]:
        with self._lock:
            return [d for d in self._drivers.values() if d.transport == transport]


import threading
