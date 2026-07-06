from __future__ import annotations

from typing import Any

from hardware.hal.interface import HardwareInterface
from core.logger import get_logger

logger = get_logger(__name__)


class HardwareRegistry:
    """Singleton-like registry for hardware drivers.

    Auto-discovers drivers and registers them with the HAL.
    """

    _instance: HardwareRegistry | None = None

    def __init__(self) -> None:
        self._drivers: dict[str, type[HardwareInterface]] = {}
        self._capabilities: dict[str, list[str]] = {}

    @classmethod
    def instance(cls) -> HardwareRegistry:
        """Return the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, driver_class: type[HardwareInterface]) -> None:
        """Register a driver class with the registry."""
        name = driver_class.__name__.lower().replace("driver", "")
        self._drivers[name] = driver_class
        try:
            instance = driver_class()
            self._capabilities[name] = instance.capabilities()
        except Exception as exc:  # pragma: no cover - simulated drivers
            logger.warning(f"Could not inspect capabilities for {name}: {exc}")
            self._capabilities[name] = []
        logger.info(f"Registered driver: {name}")

    def get(self, name: str) -> type[HardwareInterface]:
        """Retrieve a registered driver class by name."""
        driver = self._drivers.get(name)
        if driver is None:
            raise KeyError(f"Driver not found: {name}")
        return driver

    def list_registered(self) -> list[str]:
        """Return names of all registered drivers."""
        return list(self._drivers.keys())

    def discover_capabilities(self, name: str) -> list[str]:
        """Return the capabilities of a registered driver."""
        capabilities = self._capabilities.get(name)
        if capabilities is None:
            raise KeyError(f"Driver not found: {name}")
        return capabilities
