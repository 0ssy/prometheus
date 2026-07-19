from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BootChainResult:
    verified: bool
    chain_length: int
    status: str


@dataclass
class SignatureResult:
    valid: bool
    status: str


class SecureBootValidator:
    def validate_boot_chain(
        self, firmware_data: bytes, signatures: list[bytes]
    ) -> dict[str, Any]:
        result = BootChainResult(verified=False, chain_length=0, status="stub")
        logger.info(
            "SecureBoot validate_boot_chain (stub): firmware_len=%d sigs=%d",
            len(firmware_data),
            len(signatures),
        )
        return {
            "verified": result.verified,
            "chain_length": result.chain_length,
            "status": result.status,
        }

    def verify_signature(
        self, data: bytes, signature: bytes, public_key: bytes
    ) -> dict[str, Any]:
        result = SignatureResult(valid=False, status="stub")
        logger.info(
            "SecureBoot verify_signature (stub): data_len=%d sig_len=%d key_len=%d",
            len(data),
            len(signature),
            len(public_key),
        )
        return {
            "valid": result.valid,
            "status": result.status,
        }
