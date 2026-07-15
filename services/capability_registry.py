"""
Hardware capability registry (Phase 2.5 / Phase 3.5).

Registers the default hardware capabilities the roadmap promises on the
``CapabilityApi`` surface so the Rust Aether ``ToolDispatcher`` (which
POSTs to ``/capabilities/execute``) has something to call:

    hardware.connect / hardware.disconnect / hardware.read / hardware.write
    hardware.diagnose / hardware.simulate / hardware.verify
    hardware.flash / hardware.recover / hardware.reboot

Each capability is wired to the existing ``EpsilonService`` / ``EpsilonHAL``
and carries the exact permission set the ``Authorizer`` requires, so nothing
executes without authorization (Phase 1 hardening boundary).
"""

from __future__ import annotations

from typing import Any

from core.logger import get_logger
from services.epsilon_service import EpsilonService

logger = get_logger(__name__)

# Capability name -> permissions required (mirrors security/permissions.py action map).
_HARDWARE_CAPABILITIES: dict[str, set[str]] = {
    "hardware.connect": {"device.connect"},
    "hardware.disconnect": {"device.disconnect"},
    "hardware.read": {"device.read"},
    "hardware.write": {"device.write"},
    "hardware.diagnose": {"device.diagnose"},
    "hardware.simulate": {"device.simulate"},
    "hardware.verify": {"device.read"},
    "hardware.flash": {"device.flash", "ownership_declared"},
    "hardware.recover": {"device.recover", "ownership_declared"},
    "hardware.reboot": {"device.reboot", "ownership_declared"},
}


def _require_driver(hal, device_id: str):
    driver = hal.get_driver(device_id)
    if driver is None:
        raise RuntimeError(
            f"No active session for '{device_id}'. Connect it first "
            f"via the 'hardware.connect' capability."
        )
    return driver


def _forwarding_executor(executor, permissions: set[str]):
    """Wrap an executor so it forwards its permission set into EpsilonService.

    The capability layer has already authorized the caller against
    ``permissions``; passing them through satisfies EpsilonService's
    own Authorizer (which would otherwise see an empty set and deny).
    """

    def wrapper(payload: dict[str, Any]) -> dict[str, Any]:
        payload = dict(payload)
        payload["_permissions"] = set(permissions)
        return executor(payload)

    return wrapper


def register_default_hardware_capabilities(
    cap_api, epsilon: EpsilonService
) -> None:
    """Register the default hardware capabilities, delegating to HAL/Epsilon."""
    hal = epsilon._hal

    def connect(payload: dict[str, Any]) -> dict[str, Any]:
        device_id = payload.get("device_id", "virtual-0")
        driver_name = payload.get("driver_name", "virtual")
        return epsilon.connect_device(
            device_id=device_id,
            driver_name=driver_name,
            permissions=payload.get("_permissions", {"device.connect"}),
        )

    def disconnect(payload: dict[str, Any]) -> dict[str, Any]:
        device_id = payload.get("device_id", "virtual-0")
        return epsilon.disconnect_device(
            device_id=device_id,
            permissions=payload.get("_permissions", {"device.disconnect"}),
        )

    def read(payload: dict[str, Any]) -> dict[str, Any]:
        device_id = payload["device_id"]
        length = int(payload.get("length", 1024))
        driver = _require_driver(hal, device_id)
        data = driver.read(length)
        return {"device_id": device_id, "length": len(data), "data": data.hex()}

    def write(payload: dict[str, Any]) -> dict[str, Any]:
        device_id = payload["device_id"]
        raw = payload.get("data", b"")
        if isinstance(raw, str):
            raw = raw.encode()
        driver = _require_driver(hal, device_id)
        written = driver.write(raw)
        return {"device_id": device_id, "written": written}

    def diagnose(payload: dict[str, Any]) -> dict[str, Any]:
        device_id = payload["device_id"]
        return epsilon.diagnostics(device_id)

    def simulate(payload: dict[str, Any]) -> dict[str, Any]:
        device_id = payload["device_id"]
        capability = payload.get("capability", "flash")
        driver = _require_driver(hal, device_id)
        return driver.simulate(capability, payload)

    def verify(payload: dict[str, Any]) -> dict[str, Any]:
        device_id = payload.get("device_id")
        if not device_id:
            raise RuntimeError(
                "verify requires a 'device_id' for a connected device"
            )
        driver = _require_driver(hal, device_id)
        return driver.verify()

    def flash(payload: dict[str, Any]) -> dict[str, Any]:
        device_id = payload["device_id"]
        driver = _require_driver(hal, device_id)
        return driver.execute("flash", payload)

    def recover(payload: dict[str, Any]) -> dict[str, Any]:
        device_id = payload["device_id"]
        return epsilon.recovery_plan(
            device_id, risk=payload.get("risk", "high")
        )

    def reboot(payload: dict[str, Any]) -> dict[str, Any]:
        device_id = payload["device_id"]
        driver = _require_driver(hal, device_id)
        return driver.execute("reboot", payload)

    executors = {
        "hardware.connect": connect,
        "hardware.disconnect": disconnect,
        "hardware.read": read,
        "hardware.write": write,
        "hardware.diagnose": diagnose,
        "hardware.simulate": simulate,
        "hardware.verify": verify,
        "hardware.flash": flash,
        "hardware.recover": recover,
        "hardware.reboot": reboot,
    }

    # Permissions each executor forwards into the EpsilonService call. The
    # CapabilityManager has already verified the caller's granted set covers
    # these; forwarding them satisfies EpsilonService's own Authorizer
    # (which otherwise sees an empty permission set and denies).
    forward_permissions = {
        "hardware.connect": {"device.connect"},
        "hardware.disconnect": {"device.disconnect"},
        "hardware.read": {"device.read"},
        "hardware.write": {"device.write"},
        "hardware.diagnose": {"device.diagnose"},
        "hardware.simulate": {"device.simulate"},
        "hardware.verify": {"device.read"},
        "hardware.flash": {"device.flash", "ownership_declared"},
        "hardware.recover": {"device.recover", "ownership_declared"},
        "hardware.reboot": {"device.reboot", "ownership_declared"},
    }

    # Phase 4.2 expectation: EngineeringService registers discipline
    # capabilities here too; the hardware set is always registered.
    target = "hardware"
    for name, executor in executors.items():
        if cap_api.exists(name):
            continue
        cap_api.register(
            name=name,
            target=target,
            description=f"Hardware capability: {name}",
            permissions=set(_HARDWARE_CAPABILITIES[name]),
            executor=_forwarding_executor(executor, forward_permissions[name]),
        )
    logger.info(
        "Registered %d default hardware capabilities", len(executors)
    )
