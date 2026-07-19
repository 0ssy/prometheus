from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class KeyCreationResult:
    key_id: str
    algorithm: str
    status: str


@dataclass
class AttestationResult:
    pcr_indices: list[int]
    quotes: list[Any]
    status: str


@dataclass
class SealResult:
    key_id: str
    sealed: bool
    status: str


class TPMKeyStore:
    def create_key(self, key_id: str, algorithm: str = "rsa") -> dict[str, Any]:
        result = KeyCreationResult(key_id=key_id, algorithm=algorithm, status="stub")
        logger.info(
            "TPM create_key (stub): key_id=%s algorithm=%s", key_id, algorithm
        )
        return {
            "key_id": result.key_id,
            "algorithm": result.algorithm,
            "status": result.status,
        }

    def attest(self, pcr_indices: list[int]) -> dict[str, Any]:
        result = AttestationResult(pcr_indices=pcr_indices, quotes=[], status="stub")
        logger.info("TPM attest (stub): pcr_indices=%s", pcr_indices)
        return {
            "pcr_indices": result.pcr_indices,
            "quotes": result.quotes,
            "status": result.status,
        }

    def seal_data(self, data: bytes, key_id: str) -> dict[str, Any]:
        result = SealResult(key_id=key_id, sealed=True, status="stub")
        logger.info(
            "TPM seal_data (stub): key_id=%s data_len=%d", key_id, len(data)
        )
        return {
            "key_id": result.key_id,
            "sealed": result.sealed,
            "status": result.status,
        }
