from __future__ import annotations

from dataclasses import dataclass, field
import threading
import uuid

from core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class PluginPackage:
    name: str
    version: str
    description: str = ""
    author: str = ""
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    entrypoint: str = ""
    checksum: str = ""


class PluginRepository:
    def __init__(self) -> None:
        self._plugins: dict[str, PluginPackage] = {}
        self._versions: dict[str, list[str]] = {}
        self._lock = threading.RLock()
        self._logger = get_logger(__name__)

    def publish(self, package: PluginPackage) -> str:
        with self._lock:
            package_id = str(uuid.uuid4())
            self._plugins[package_id] = package
            self._versions.setdefault(package.name, []).append(package.version)
            self._logger.info(
                f"Published plugin: {package.name} v{package.version}"
            )
            return package_id

    def install(self, package_name: str, version: str) -> PluginPackage:
        with self._lock:
            for pkg in self._plugins.values():
                if pkg.name == package_name and pkg.version == version:
                    self._logger.info(
                        f"Installed plugin: {package_name} v{version}"
                    )
                    return pkg
            raise ValueError(f"Plugin not found: {package_name}=={version}")

    def list_available(self) -> list[PluginPackage]:
        with self._lock:
            return list(self._plugins.values())

    def search(self, query: str) -> list[PluginPackage]:
        with self._lock:
            q = query.lower()
            return [
                p
                for p in self._plugins.values()
                if q in p.name.lower() or q in p.description.lower()
            ]

    def get_versions(self, package_name: str) -> list[str]:
        with self._lock:
            return list(self._versions.get(package_name, []))

    def uninstall(self, package_id: str) -> bool:
        with self._lock:
            pkg = self._plugins.pop(package_id, None)
            if pkg:
                self._logger.info(
                    f"Uninstalled plugin: {pkg.name} ({package_id})"
                )
                return True
            return False
