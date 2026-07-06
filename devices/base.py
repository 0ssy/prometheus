"""
Prometheus Device — Base Contract (RFC 0001)
-----------------------------------------
Every transport (simulated, serial, later Wi-Fi/GPIO/USB/Bluetooth)
implements this same shape. Agents and plugins go through the
DeviceRegistry and this interface only — they never import pyserial,
bleak, or any transport-specific library directly. That's what lets
a plugin written against a SimulatedDevice keep working unchanged
once a real ESP32 shows up.

Deviation from RFC 0001's sketch: the RFC wrote this as async. Phase
Alpha's scheduler is a plain background thread, not asyncio, and
pyserial itself is blocking — so v0.1 keeps this synchronous to match
the rest of the codebase's actual concurrency model. Revisit async
if/when Wi-Fi or multi-device polling actually needs it.

ownership_declared exists because of RFC 0000: for v0.1 this is an
honor-system flag the caller sets at registration time, NOT a verified
guarantee. Every place this field is surfaced (API, logs) must call it
"declared", not "verified" — see RFC 0000 for why that distinction
matters.
"""
from abc import ABC, abstractmethod
from typing import Any


class Device(ABC):
    device_id: str
    transport: str  # "simulated" | "serial" | "wifi" | "gpio" | "usb" | "bluetooth"
    ownership_declared: bool = False

    @abstractmethod
    def connect(self) -> None:
        """Open the connection. Idempotent — safe to call if already connected."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection. Idempotent — safe to call if already disconnected."""
        ...

    @abstractmethod
    def read(self) -> Any:
        """Read the latest available data from the device."""
        ...

    @abstractmethod
    def write(self, payload: Any) -> None:
        """Send data to the device."""
        ...

    @abstractmethod
    def status(self) -> dict:
        """Return current connection/state info. Must be JSON-serializable."""
        ...