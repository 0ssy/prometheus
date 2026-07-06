from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from hardware.hal.interface import HardwareInterface
from core.logger import get_logger

logger = get_logger(__name__)


class HALManager:
    """Manages the lifecycle of hardware interfaces."""

    def __init__(self) -> None:
        self._interfaces: dict[str, HardwareInterface] = {}
        self._lock = threading.Lock()

    def register_interface(self, name: str, interface: HardwareInterface) -> None:
        """Register a hardware interface by name."""
        with self._lock:
            self._interfaces[name] = interface
            logger.info(f"Registered hardware interface: {name}")

    def get_interface(self, name: str) -> HardwareInterface:
        """Retrieve a registered hardware interface by name."""
        with self._lock:
            interface = self._interfaces.get(name)
            if interface is None:
                raise KeyError(f"Hardware interface not found: {name}")
            return interface

    def list_interfaces(self) -> list[str]:
        """Return names of all registered hardware interfaces."""
        with self._lock:
            return list(self._interfaces.keys())

    def unregister_interface(self, name: str) -> None:
        """Remove a registered hardware interface by name."""
        with self._lock:
            if name in self._interfaces:
                del self._interfaces[name]
                logger.info(f"Unregistered hardware interface: {name}")
            else:
                raise KeyError(f"Hardware interface not found: {name}")
