from __future__ import annotations

import warnings

warnings.warn(
    "devices.base is deprecated. Import HardwareInterface from hardware.hal.interface instead. "
    "This module will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Device(ABC):
    device_id: str
    transport: str = ""
    ownership_declared: bool = False
    latency_seconds: float = 0.0
    failure_rate: float = 0.0
    _connected: bool = field(default=False, repr=False)

    @abstractmethod
    def connect(self) -> None:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    @abstractmethod
    def read(self) -> Any:
        ...

    @abstractmethod
    def write(self, payload: Any) -> None:
        ...

    @abstractmethod
    def status(self) -> dict[str, Any]:
        ...

    def diagnose(self) -> dict[str, Any]:
        return {"supported": False}

    def verify(self) -> dict[str, Any]:
        return {"supported": False}

    def recover(self) -> dict[str, Any]:
        return {"supported": False}
