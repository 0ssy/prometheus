import pytest

from api.capability_api import CapabilityApi
from core.capabilities import CapabilityManager


def test_capability_manager_implements_contract():
    manager = CapabilityManager()
    assert isinstance(manager, CapabilityApi)


def test_register_discover_and_exists():
    manager = CapabilityManager()
    manager.register(
        name="device.dev1.status",
        target="device:dev1",
        description="Get status",
        permissions={"device.status"},
        executor=lambda _: {"ok": True},
    )

    assert manager.exists("device.dev1.status")
    capabilities = manager.discover(prefix="device.dev1")
    assert len(capabilities) == 1
    assert capabilities[0]["name"] == "device.dev1.status"


def test_authorize_and_execute_success():
    manager = CapabilityManager()
    manager.register(
        name="device.dev1.read",
        target="device:dev1",
        description="Read",
        permissions={"device.read"},
        executor=lambda _: {"value": "abc"},
    )

    assert manager.authorize("device.dev1.read", {"device.read"})
    result = manager.execute(
        "device.dev1.read", payload={}, granted_permissions={"device.read"}
    )

    assert result == {"value": "abc"}
    history = manager.history("device.dev1.read")
    assert len(history) == 1
    assert history[0]["success"] is True


def test_execute_denied_when_missing_permissions():
    manager = CapabilityManager()
    manager.register(
        name="device.dev1.write",
        target="device:dev1",
        description="Write",
        permissions={"device.write"},
        executor=lambda payload: payload["value"],
    )

    with pytest.raises(PermissionError, match="Missing permissions"):
        manager.execute("device.dev1.write", payload={"value": "x"}, granted_permissions=set())

    history = manager.history("device.dev1.write")
    assert len(history) == 1
    assert history[0]["success"] is False


def test_duplicate_registration_raises():
    manager = CapabilityManager()
    manager.register(
        name="device.dev1.status",
        target="device:dev1",
        description="Get status",
        permissions={"device.status"},
        executor=lambda _: {"ok": True},
    )

    with pytest.raises(ValueError, match="already registered"):
        manager.register(
            name="device.dev1.status",
            target="device:dev1",
            description="Get status",
            permissions={"device.status"},
            executor=lambda _: {"ok": True},
        )
