from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from core.logger import get_logger

logger = get_logger(__name__)


@runtime_checkable
class EngineeringModule(Protocol):
    """Protocol that all engineering discipline modules must implement."""

    name: str

    def execute(self, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...


class EngineeringService:
    """Single entry point for all engineering disciplines.

    Wraps the standalone Gamma utilities in `engineering/` and exposes
    them through a unified interface. No discipline module imports
    `hardware/` directly.
    """

    def __init__(self) -> None:
        self._modules: dict[str, EngineeringModule] = {}
        self._register_default_modules()

    def _register_default_modules(self) -> None:
        from engineering.firmware_inspector import inspect_firmware
        from engineering.boot_chain import analyze_boot_chain
        from engineering.partition_mapper import read_partition_table
        from engineering.recovery_planner import plan_recovery
        from engineering.crypto_verify import sha256_hex, verify_ed25519
        from engineering.embedded import EmbeddedModule
        from engineering.robotics import RoboticsModule
        from engineering.mechanical import MechanicalModule
        from engineering.electrical import ElectricalModule
        from engineering.networking import NetworkingModule
        from engineering.cybersecurity import CybersecurityModule
        from engineering.ai import AIModule
        from engineering.data import DataModule
        from engineering.cloud import CloudModule

        self.register_module("firmware", _FirmwareModule(inspect_firmware))
        self.register_module("boot_chain", _BootChainModule(analyze_boot_chain))
        self.register_module("partition", _PartitionModule(read_partition_table))
        self.register_module("recovery", _RecoveryModule(plan_recovery))
        self.register_module("crypto", _CryptoModule(sha256_hex, verify_ed25519))
        self.register_module("embedded", EmbeddedModule())
        self.register_module("robotics", RoboticsModule())
        self.register_module("mechanical", MechanicalModule())
        self.register_module("electrical", ElectricalModule())
        self.register_module("networking", NetworkingModule())
        self.register_module("cybersecurity", CybersecurityModule())
        self.register_module("ai", AIModule())
        self.register_module("data", DataModule())
        self.register_module("cloud", CloudModule())

    def register_module(self, name: str, module: EngineeringModule) -> None:
        self._modules[name] = module
        logger.info("Registered engineering module: %s", name)

    def list_modules(self) -> list[str]:
        return list(self._modules.keys())

    def execute_workflow(self, module_name: str, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        module = self._modules.get(module_name)
        if module is None:
            raise ValueError(f"Unknown engineering module: {module_name}")
        return module.execute(workflow, payload)


class _FirmwareModule:
    name = "firmware"

    def __init__(self, inspect_func):
        self._inspect = inspect_func

    def execute(self, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        if workflow == "inspect":
            path = payload.get("path", "")
            ownership_declared = payload.get("ownership_declared", False)
            report = self._inspect(path, ownership_declared=ownership_declared)
            return report.to_dict()
        raise ValueError(f"Unknown firmware workflow: {workflow}")


class _BootChainModule:
    name = "boot_chain"

    def __init__(self, analyze_func):
        self._analyze = analyze_func

    def execute(self, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        if workflow == "analyze":
            firmware_bytes = payload.get("firmware_bytes", b"")
            signature = payload.get("signature")
            public_key_bytes = payload.get("public_key_bytes")
            result = self._analyze(firmware_bytes, signature, public_key_bytes)
            return result.to_dict()
        raise ValueError(f"Unknown boot_chain workflow: {workflow}")


class _PartitionModule:
    name = "partition"

    def __init__(self, read_func):
        self._read = read_func

    def execute(self, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        if workflow == "read_table":
            disk_path = payload.get("disk_path", "")
            ownership_declared = payload.get("ownership_declared", False)
            sector_size = payload.get("sector_size", 512)
            table = self._read(disk_path, ownership_declared=ownership_declared, sector_size=sector_size)
            return table.to_dict()
        raise ValueError(f"Unknown partition workflow: {workflow}")


class _RecoveryModule:
    name = "recovery"

    def __init__(self, plan_func):
        self._plan = plan_func

    def execute(self, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        if workflow == "plan":
            device_id = payload.get("device_id", "")
            boot_chain_status = payload.get("boot_chain_status", "unknown")
            partition_scheme = payload.get("partition_scheme", "unknown")
            plan = self._plan(device_id, boot_chain_status, partition_scheme)
            return plan.to_dict()
        raise ValueError(f"Unknown recovery workflow: {workflow}")


class _CryptoModule:
    name = "crypto"

    def __init__(self, sha256_func, verify_func):
        self._sha256 = sha256_func
        self._verify = verify_func

    def execute(self, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        if workflow == "sha256":
            data = payload.get("data", b"")
            return {"hash": self._sha256(data)}
        if workflow == "verify":
            public_key_bytes = payload.get("public_key_bytes", b"")
            signature = payload.get("signature", b"")
            data = payload.get("data", b"")
            return {"valid": self._verify(public_key_bytes, signature, data)}
        raise ValueError(f"Unknown crypto workflow: {workflow}")
