from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class HardwareInterface(ABC):
    """Abstract base class for all hardware interfaces."""

    @abstractmethod
    def connect(self) -> dict[str, Any]:
        """Establish connection to the hardware device."""
        ...

    @abstractmethod
    def disconnect(self) -> dict[str, Any]:
        """Terminate connection to the hardware device."""
        ...

    @abstractmethod
    def identify(self) -> dict[str, Any]:
        """Return identifying information about the hardware device."""
        ...

    @abstractmethod
    def capabilities(self) -> list[str]:
        """Return a list of supported capabilities for this interface."""
        ...

    @abstractmethod
    def execute(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute a specific capability with the given payload."""
        ...

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Return health metrics for the connected device."""
        ...

    @abstractmethod
    def diagnostics(self) -> dict[str, Any]:
        """Run diagnostics on the connected device."""
        ...
