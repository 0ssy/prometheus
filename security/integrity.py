"""
Security: Integrity (Epsilon / Hephaestus phase)
------------------------------------------------
Verifies data/artifact integrity for hardware operations via hashing and
provides a lightweight attestation mechanism.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class IntegrityCheck:
    check_id: str
    timestamp: datetime
    target: str
    expected_hash: str
    actual_hash: str
    passed: bool
    algorithm: str


@dataclass
class AttestationResult:
    attested: bool
    timestamp: datetime
    data_hash: str
    metadata: dict[str, Any]
    signature: str


class IntegrityVerifier:
    def __init__(self) -> None:
        self._supported = hashlib.algorithms_available

    def compute_hash(self, data: bytes, algorithm: str = "sha256") -> str:
        if algorithm not in self._supported:
            raise ValueError(f"Unsupported hash algorithm: {algorithm!r}")
        hasher = hashlib.new(algorithm)
        hasher.update(data)
        digest = hasher.hexdigest()
        logger.debug("Computed %s hash (%d bytes)", algorithm, len(data))
        return digest

    def verify(
        self,
        target: str,
        expected_hash: str,
        algorithm: str = "sha256",
        data: bytes | None = None,
    ) -> IntegrityCheck:
        actual_hash = self.compute_hash(data or b"", algorithm) if data is not None else ""
        passed = bool(actual_hash) and actual_hash == expected_hash
        check = IntegrityCheck(
            check_id=str(uuid.uuid4()),
            timestamp=_utc_now(),
            target=target,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            passed=passed,
            algorithm=algorithm,
        )
        logger.info(
            "Integrity check %s: target=%s passed=%s",
            check.check_id,
            target,
            passed,
        )
        return check

    def attest(self, data: bytes, metadata: dict[str, Any]) -> dict[str, Any]:
        data_hash = self.compute_hash(data)
        signature = uuid.uuid4().hex
        result = AttestationResult(
            attested=True,
            timestamp=_utc_now(),
            data_hash=data_hash,
            metadata=dict(metadata),
            signature=signature,
        )
        logger.info("Attested data (hash=%s)", data_hash)
        return {
            "attested": result.attested,
            "timestamp": result.timestamp.isoformat(),
            "data_hash": result.data_hash,
            "metadata": result.metadata,
            "signature": result.signature,
        }
