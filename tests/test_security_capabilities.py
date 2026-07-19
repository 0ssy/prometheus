from __future__ import annotations

import pytest

from core.capabilities import CapabilityManager
from services.security_capabilities import register_security_capabilities


def _build_manager() -> CapabilityManager:
    manager = CapabilityManager()
    register_security_capabilities(manager)
    return manager


def test_security_capabilities_registered():
    manager = _build_manager()
    names = {
        "security.sandbox.execute",
        "security.sandbox.validate_plugin",
        "security.boot.validate_chain",
        "security.boot.verify_signature",
        "security.tpm.create_key",
        "security.tpm.attest",
        "security.tpm.seal",
    }
    assert names.issubset({c["name"] for c in manager.discover(target="security")})


def test_security_sandbox_execute():
    manager = _build_manager()
    result = manager.execute(
        "security.sandbox.execute",
        payload={"code": "print('hello')", "language": "python", "timeout_seconds": 5},
        granted_permissions={"plugin.execute"},
    )
    assert result["status"] == "stub"
    assert result["code"] == "print('hello')"
    assert result["language"] == "python"


def test_security_sandbox_validate_plugin():
    manager = _build_manager()
    result = manager.execute(
        "security.sandbox.validate_plugin",
        payload={"plugin_path": "/tmp/plugin.py"},
        granted_permissions={"plugin.execute"},
    )
    assert result["status"] == "stub"
    assert result["plugin_path"] == "/tmp/plugin.py"
    assert result["safe"] is True


def test_security_boot_validate_chain():
    manager = _build_manager()
    result = manager.execute(
        "security.boot.validate_chain",
        payload={"firmware_data": b"firmware", "signatures": [b"sig"]},
        granted_permissions={"firmware.read"},
    )
    assert result["status"] == "stub"
    assert result["verified"] is False
    assert result["chain_length"] == 0


def test_security_boot_verify_signature():
    manager = _build_manager()
    result = manager.execute(
        "security.boot.verify_signature",
        payload={"data": b"data", "signature": b"sig", "public_key": b"key"},
        granted_permissions={"firmware.read"},
    )
    assert result["status"] == "stub"
    assert result["valid"] is False


def test_security_tpm_create_key():
    manager = _build_manager()
    result = manager.execute(
        "security.tpm.create_key",
        payload={"key_id": "key-1", "algorithm": "rsa"},
        granted_permissions={"device.connect"},
    )
    assert result["status"] == "stub"
    assert result["key_id"] == "key-1"
    assert result["algorithm"] == "rsa"


def test_security_tpm_attest():
    manager = _build_manager()
    result = manager.execute(
        "security.tpm.attest",
        payload={"pcr_indices": [0, 1, 2]},
        granted_permissions={"device.connect"},
    )
    assert result["status"] == "stub"
    assert result["pcr_indices"] == [0, 1, 2]
    assert result["quotes"] == []


def test_security_tpm_seal():
    manager = _build_manager()
    result = manager.execute(
        "security.tpm.seal",
        payload={"data": b"secret", "key_id": "key-1"},
        granted_permissions={"device.connect"},
    )
    assert result["status"] == "stub"
    assert result["key_id"] == "key-1"
    assert result["sealed"] is True


def test_security_capabilities_require_permissions():
    manager = _build_manager()
    with pytest.raises(PermissionError, match="Missing permissions"):
        manager.execute(
            "security.sandbox.execute",
            payload={"code": "print('hello')"},
            granted_permissions=set(),
        )
