"""
Integration test for the capability layer (Phase 2.5 / Phase 3.5).

Validates the exact Python path the Rust Aether ``ToolDispatcher`` hits
when it POSTs to ``/capabilities/execute``:

    connect (virtual) -> diagnose -> read -> verify -> disconnect

and that authorization is enforced (a flash without ownership is denied).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from api.events import CapabilityExecutedEvent
from core.bootstrap import boot


@pytest.fixture()
def container():
    with patch("core.bootstrap.init_db"):
        c = boot(lambda: None)
    yield c
    c.get("scheduler").stop()


def _granted(*names: str) -> set[str]:
    return set(names)


def test_default_hardware_capabilities_registered(container) -> None:
    cap_api = container.get("capability_api")
    names = {c["name"] for c in cap_api.discover(prefix="hardware.")}
    assert {
        "hardware.connect",
        "hardware.disconnect",
        "hardware.read",
        "hardware.write",
        "hardware.diagnose",
        "hardware.simulate",
        "hardware.verify",
        "hardware.flash",
        "hardware.recover",
        "hardware.reboot",
    }.issubset(names)


def test_full_hardware_workflow(container) -> None:
    platform = container.get("platform_service")
    device_id = "cap-test-0"

    events: list[CapabilityExecutedEvent] = []
    container.get("event_bus").subscribe(
        "capability.executed", lambda e: events.append(e)
    )

    # connect
    res = platform.execute_capability(
        capability_name="hardware.connect",
        payload={"device_id": device_id, "driver_name": "virtual"},
        granted_permissions=_granted("device.connect"),
    )
    assert res["device_id"] == device_id

    # diagnose
    diag = platform.execute_capability(
        capability_name="hardware.diagnose",
        payload={"device_id": device_id},
        granted_permissions=_granted("device.diagnose"),
    )
    assert isinstance(diag, dict)
    assert "connectivity" in diag

    # read
    read = platform.execute_capability(
        capability_name="hardware.read",
        payload={"device_id": device_id},
        granted_permissions=_granted("device.read"),
    )
    assert read["device_id"] == device_id

    # verify
    ver = platform.execute_capability(
        capability_name="hardware.verify",
        payload={"device_id": device_id},
        granted_permissions=_granted("device.read"),
    )
    assert ver["verified"] is True

    # disconnect
    platform.execute_capability(
        capability_name="hardware.disconnect",
        payload={"device_id": device_id},
        granted_permissions=_granted("device.disconnect"),
    )

    # Each successful execution published an event.
    assert len(events) == 5
    assert all(e.success for e in events)


def test_flash_denied_without_ownership(container) -> None:
    platform = container.get("platform_service")
    device_id = "cap-test-1"
    platform.execute_capability(
        capability_name="hardware.connect",
        payload={"device_id": device_id, "driver_name": "virtual"},
        granted_permissions=_granted("device.connect"),
    )
    # Flash requires device.flash AND ownership_declared.
    with pytest.raises(PermissionError):
        platform.execute_capability(
            capability_name="hardware.flash",
            payload={"device_id": device_id},
            granted_permissions=_granted("device.flash"),
        )
