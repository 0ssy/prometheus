from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import threading
import uuid

from core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class CapabilityPackage:
    name: str
    version: str
    description: str = ""
    interface: str = ""
    permissions: list[str] = field(default_factory=list)
    implementation: Any = None


class CapabilityRepository:
    def __init__(self) -> None:
        self._capabilities: dict[str, CapabilityPackage] = {}
        self._by_interface: dict[str, list[str]] = {}
        self._lock = threading.RLock()
        self._logger = get_logger(__name__)

    def register(self, capability: CapabilityPackage) -> str:
        with self._lock:
            cid = str(uuid.uuid4())
            self._capabilities[cid] = capability
            self._by_interface.setdefault(capability.interface, []).append(cid)
            self._logger.info(
                f"Registered capability: {capability.name} v{capability.version}"
            )
            return cid

    def discover(
        self, prefix: str | None = None, target: str | None = None
    ) -> list[CapabilityPackage]:
        with self._lock:
            results = list(self._capabilities.values())
            if prefix:
                results = [c for c in results if c.name.startswith(prefix)]
            if target:
                results = [
                    c for c in results if target in c.name or target in c.interface
                ]
            return results

    def get(self, name: str) -> CapabilityPackage | None:
        with self._lock:
            for cap in self._capabilities.values():
                if cap.name == name:
                    return cap
            return None

    def list_by_interface(self, interface_name: str) -> list[CapabilityPackage]:
        with self._lock:
            return [
                self._capabilities[cid]
                for cid in self._by_interface.get(interface_name, [])
                if cid in self._capabilities
            ]
