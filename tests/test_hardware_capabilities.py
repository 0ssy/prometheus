"""
Tests for the extended hardware transport capabilities (Phase 4.2).

Validates that the transport-layer capabilities registered by
``services.hardware_capabilities`` are discoverable, carry the correct
permissions, and return the expected stub response.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.capabilities import CapabilityManager
from services.hardware_capabilities import (
    _TRANSPORT_CAPABILITIES,
    register_default_hardware_capabilities,
)


def _granted(*names: str) -> set[str]:
    return set(names)


@pytest.fixture()
def manager():
    m = CapabilityManager()
    register_default_hardware_capabilities(m, epsilon=MagicMock())
    return m


def test_all_transport_capabilities_registered(manager) -> None:
    names = {c["name"] for c in manager.discover(prefix="hardware.transport.")}
    assert set(_TRANSPORT_CAPABILITIES) == names


def test_transport_capabilities_discoverable_with_prefix(manager) -> None:
    discovered = manager.discover(prefix="hardware.transport.")
    assert all(c["name"].startswith("hardware.transport.") for c in discovered)
    assert len(discovered) == len(_TRANSPORT_CAPABILITIES)


@pytest.mark.parametrize("name,permissions", list(_TRANSPORT_CAPABILITIES.items()))
def test_each_capability_executes_with_correct_permissions(manager, name, permissions) -> None:
    assert manager.exists(name)
    assert manager.authorize(name, _granted(*permissions))
    result = manager.execute(name, payload={}, granted_permissions=_granted(*permissions))
    assert result == {
        "status": "not_implemented",
        "capability": name,
        "message": "Transport layer stub",
    }


@pytest.mark.parametrize("name,permissions", list(_TRANSPORT_CAPABILITIES.items()))
def test_execution_denied_without_permissions(manager, name, permissions) -> None:
    missing = _granted() if permissions else _granted()
    with pytest.raises(PermissionError):
        manager.execute(name, payload={}, granted_permissions=missing)
