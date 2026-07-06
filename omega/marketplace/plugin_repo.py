from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PluginPackage:
    name: str
    version: str
    description: str
    author: str
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    entrypoint: str = ""
    checksum: str = ""


class PluginRepository:
    def __init__(self) -> None:
        self._plugins: dict[str, PluginPackage] = {}
        self._lock = threading.RLock()

    def publish(self, package: PluginPackage) -> str:
        package_id = f"{package.name}@{package.version}"
        with self._lock:
            self._plugins[package_id] = package
            logger.info("Published plugin: %s", package_id)
        return package_id

    def install(self, package_name: str, version: str) -> PluginPackage:
        package_id = f"{package_name}@{version}"
        with self._lock:
            package = self._plugins.get(package_id)
            if package is None:
                raise RuntimeError(f"Plugin not found: {package_id}")
            return package

    def list_available(self) -> list[PluginPackage]:
        with self._lock:
            return list(self._plugins.values())

    def search(self, query: str) -> list[PluginPackage]:
        with self._lock:
            return [p for p in self._plugins.values() if query.lower() in p.name.lower() or query.lower() in p.description.lower()]

    def get_versions(self, package_name: str) -> list[str]:
        with self._lock:
            return [p.version for p in self._plugins.values() if p.name == package_name]

    def uninstall(self, package_id: str) -> bool:
        with self._lock:
            if package_id in self._plugins:
                del self._plugins[package_id]
                return True
            return False


import threading
