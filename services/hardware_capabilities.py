"""
Hardware transport capabilities (Phase 4.2).

Registers the transport-layer hardware capabilities beyond the basic
``hardware.*`` surface wired in ``capability_registry``. These expose the
per-bus transports (USB, Bluetooth, CAN, UART, SPI, I2C, GPIO, NFC, LoRa,
Zigbee) the roadmap promises, each gated behind the matching device
permission set the ``Authorizer`` requires.

Each transport executor is a stub returning
``{"status": "not_implemented", "capability": name, "message": ...}`` until
the corresponding bus driver is implemented.
"""

from __future__ import annotations

from typing import Any

from core.logger import get_logger
from services.capability_registry import (
    register_default_hardware_capabilities as _register_base_hardware_capabilities,
)
from services.epsilon_service import EpsilonService

logger = get_logger(__name__)

# Capability name -> permissions required (mirrors security/permissions.py action map).
_TRANSPORT_CAPABILITIES: dict[str, set[str]] = {
    "hardware.transport.usb.enumerate": {"device.connect"},
    "hardware.transport.bluetooth.scan": {"device.connect"},
    "hardware.transport.can.read": {"device.read"},
    "hardware.transport.can.write": {"device.write"},
    "hardware.transport.uart.read": {"device.read"},
    "hardware.transport.uart.write": {"device.write"},
    "hardware.transport.spi.read": {"device.read"},
    "hardware.transport.spi.write": {"device.write"},
    "hardware.transport.i2c.read": {"device.read"},
    "hardware.transport.i2c.write": {"device.write"},
    "hardware.transport.gpio.read": {"device.read"},
    "hardware.transport.gpio.write": {"device.write"},
    "hardware.transport.nfc.enumerate": {"device.connect"},
    "hardware.transport.lora.transmit": {"device.write"},
    "hardware.transport.zigbee.scan": {"device.connect"},
}


def register_default_hardware_capabilities(
    cap_api, epsilon: EpsilonService
) -> None:
    """Register the extended hardware transport capabilities (stubs)."""
    _register_base_hardware_capabilities(cap_api, epsilon)

    def make_executor(name: str):
        def executor(payload: dict[str, Any]) -> dict[str, Any]:
            return {
                "status": "not_implemented",
                "capability": name,
                "message": "Transport layer stub",
            }

        return executor

    target = "hardware.transport"
    for name, permissions in _TRANSPORT_CAPABILITIES.items():
        if cap_api.exists(name):
            continue
        cap_api.register(
            name=name,
            target=target,
            description=f"Hardware transport capability: {name}",
            permissions=set(permissions),
            executor=make_executor(name),
        )
    logger.info(
        "Registered %d hardware transport capabilities",
        len(_TRANSPORT_CAPABILITIES),
    )
