from __future__ import annotations

from dataclasses import dataclass, field
import threading

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CapabilityPackage:
    name: str
    version: str
    description: str
    interface: str
    permissions: list[str] = field(default_factory=list)
    implementation: str = ""


class CapabilityRepository:
    def __init__(self) -> None:
        self._capabilities: dict[str, CapabilityPackage] = {}
        self._lock = threading.RLock()

    def register(self, capability: CapabilityPackage) -> str:
        cap_id = f"{capability.name}@{capability.version}"
        with self._lock:
            self._capabilities[cap_id] = capability
            logger.info("Registered capability: %s", cap_id)
        return cap_id

    def discover(self, prefix: str | None = None, target: str | None = None) -> list[CapabilityPackage]:
        with self._lock:
            results = list(self._capabilities.values())
            if prefix:
                results = [c for c in results if c.name.startswith(prefix)]
            if target:
                results = [c for c in results if target in c.description or target in c.name]
            return results

    def get(self, name: str) -> CapabilityPackage | None:
        with self._lock:
            for cap in self._capabilities.values():
                if cap.name == name:
                    return cap
            return None

    def list_by_interface(self, interface_name: str) -> list[CapabilityPackage]:
        with self._lock:
            return [c for c in self._capabilities.values() if c.interface == interface_name]
