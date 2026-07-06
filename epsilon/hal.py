from __future__ import annotations

from typing import Any

from hardware.hal.manager import HALManager
from hardware.hal.registry import HardwareRegistry
from hardware.hal.capability_mapper import CapabilityMapper
from hardware.drivers.base import HardwareDriver
from core.logger import get_logger

logger = get_logger(__name__)


class EpsilonHAL:
    """Epsilon Hardware Abstraction Layer bridge.

    Wraps the lower-level hardware HAL and exposes it to the rest of the
    Prometheus Core platform. No code outside this module talks directly to
    USB, Bluetooth, ADB, or other transports.
    """

    def __init__(self) -> None:
        self._manager = HALManager()
        self._registry = HardwareRegistry.instance()
        self._mapper = CapabilityMapper()
        self._drivers: dict[str, type[HardwareDriver]] = {}
        self._register_default_drivers()

    def _register_default_drivers(self) -> None:
        """Register default driver classes with the registry."""
        from hardware.drivers.usb import USBDriver
        from hardware.drivers.adb import ADBDriver
        from hardware.drivers.fastboot import FastbootDriver
        from hardware.drivers.network import NetworkDriver
        from hardware.drivers.virtual import VirtualDriver

        default_drivers = [
            USBDriver,
            ADBDriver,
            FastbootDriver,
            NetworkDriver,
            VirtualDriver,
        ]
        for driver_cls in default_drivers:
            self._registry.register(driver_cls)
            self._drivers[driver_cls.__name__.lower()] = driver_cls

    def register_interface(self, name: str, driver_cls: type[HardwareDriver]) -> None:
        self._registry.register(driver_cls)
        self._drivers[name.lower()] = driver_cls

    def list_interfaces(self) -> list[dict[str, Any]]:
        result = []
        for name in self._registry.list_registered():
            capabilities = self._registry.discover_capabilities(name)
            result.append({"name": name, "capabilities": capabilities})
        return result

    def get_interface(self, name: str) -> type[HardwareDriver]:
        return self._registry.get(name)

    def instantiate_driver(self, name: str, **kwargs: Any) -> HardwareDriver:
        driver_cls = self.get_interface(name)
        driver = driver_cls(**kwargs)
        self._manager.register_interface(name, driver)
        return driver

    def discover_capabilities(self, driver_name: str) -> list[str]:
        return self._registry.discover_capabilities(driver_name)
