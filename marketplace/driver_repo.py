from __future__ import annotations

from dataclasses import dataclass, field
import threading
import uuid

from core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class DriverPackage:
    name: str
    version: str
    transport: str = ""
    supported_devices: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    checksum: str = ""


class DriverRepository:
    def __init__(self) -> None:
        self._drivers: dict[str, DriverPackage] = {}
        self._by_transport: dict[str, list[str]] = {}
        self._lock = threading.RLock()
        self._logger = get_logger(__name__)

    def register(self, driver: DriverPackage) -> str:
        with self._lock:
            did = str(uuid.uuid4())
            self._drivers[did] = driver
            self._by_transport.setdefault(driver.transport, []).append(did)
            self._logger.info(
                f"Registered driver: {driver.name} v{driver.version}"
            )
            return did

    def discover(self, transport: str | None = None) -> list[DriverPackage]:
        with self._lock:
            results = list(self._drivers.values())
            if transport:
                results = [d for d in results if d.transport == transport]
            return results

    def get(self, name: str) -> DriverPackage | None:
        with self._lock:
            for drv in self._drivers.values():
                if drv.name == name:
                    return drv
            return None

    def list_by_transport(self, transport: str) -> list[DriverPackage]:
        with self._lock:
            return [
                self._drivers[did]
                for did in self._by_transport.get(transport, [])
                if did in self._drivers
            ]
