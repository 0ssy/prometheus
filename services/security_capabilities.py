from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)

_SECURITY_CAPABILITIES: dict[str, set[str]] = {
    "security.sandbox.execute": {"plugin.execute"},
    "security.sandbox.validate_plugin": {"plugin.execute"},
    "security.boot.validate_chain": {"firmware.read"},
    "security.boot.verify_signature": {"firmware.read"},
    "security.tpm.create_key": {"device.connect"},
    "security.tpm.attest": {"device.connect"},
    "security.tpm.seal": {"device.connect"},
}


def _build_sandbox_executor():
    from security.sandbox import SandboxManager

    manager = SandboxManager()

    def execute(payload: dict[str, Any]) -> dict[str, Any]:
        return manager.execute_isolated(
            code=payload.get("code", ""),
            language=payload.get("language", "python"),
            timeout_seconds=int(payload.get("timeout_seconds", 5)),
        )

    def validate_plugin(payload: dict[str, Any]) -> dict[str, Any]:
        return manager.validate_plugin(
            plugin_path=payload.get("plugin_path", ""),
        )

    return {
        "security.sandbox.execute": execute,
        "security.sandbox.validate_plugin": validate_plugin,
    }


def _build_boot_executor():
    from security.secure_boot import SecureBootValidator

    validator = SecureBootValidator()

    def validate_chain(payload: dict[str, Any]) -> dict[str, Any]:
        firmware_data = payload.get("firmware_data", b"")
        if isinstance(firmware_data, str):
            firmware_data = firmware_data.encode()
        signatures = payload.get("signatures", [])
        if signatures and isinstance(signatures[0], str):
            signatures = [s.encode() for s in signatures]
        return validator.validate_boot_chain(
            firmware_data=firmware_data,
            signatures=signatures,
        )

    def verify_signature(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data", b"")
        if isinstance(data, str):
            data = data.encode()
        signature = payload.get("signature", b"")
        if isinstance(signature, str):
            signature = signature.encode()
        public_key = payload.get("public_key", b"")
        if isinstance(public_key, str):
            public_key = public_key.encode()
        return validator.verify_signature(
            data=data, signature=signature, public_key=public_key
        )

    return {
        "security.boot.validate_chain": validate_chain,
        "security.boot.verify_signature": verify_signature,
    }


def _build_tpm_executor():
    from security.tpm import TPMKeyStore

    store = TPMKeyStore()

    def create_key(payload: dict[str, Any]) -> dict[str, Any]:
        return store.create_key(
            key_id=payload.get("key_id", ""),
            algorithm=payload.get("algorithm", "rsa"),
        )

    def attest(payload: dict[str, Any]) -> dict[str, Any]:
        pcr_indices = payload.get("pcr_indices", [])
        return store.attest(pcr_indices=pcr_indices)

    def seal(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data", b"")
        if isinstance(data, str):
            data = data.encode()
        return store.seal_data(data=data, key_id=payload.get("key_id", ""))

    return {
        "security.tpm.create_key": create_key,
        "security.tpm.attest": attest,
        "security.tpm.seal": seal,
    }


def register_security_capabilities(cap_api) -> None:
    executors = {}
    executors.update(_build_sandbox_executor())
    executors.update(_build_boot_executor())
    executors.update(_build_tpm_executor())

    target = "security"
    for name, executor in executors.items():
        if cap_api.exists(name):
            continue
        cap_api.register(
            name=name,
            target=target,
            description=f"Security capability: {name}",
            permissions=set(_SECURITY_CAPABILITIES[name]),
            executor=executor,
        )
    logger.info("Registered %d security capabilities", len(executors))
