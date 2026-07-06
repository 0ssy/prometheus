"""
Boot Chain Analyzer (RFC 0002)
-----------------------------------------
Verifies a signature against known public keys. Reports one of
valid / invalid / unknown. Never attempts to forge a signature, patch
around a broken chain, or otherwise route around a failed check.

READ-ONLY, same as partition_mapper.py and firmware_inspector.py.
"""

from dataclasses import dataclass, asdict
from .crypto_verify import verify_ed25519, sha256_hex
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BootChainResult:
    status: str  # "valid" | "invalid" | "unknown"
    firmware_hash: str
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


def analyze_boot_chain(
    firmware_bytes: bytes, signature: bytes | None, public_key_bytes: bytes | None
) -> BootChainResult:
    firmware_hash = sha256_hex(firmware_bytes)

    if signature is None or public_key_bytes is None:
        logger.info(
            "Boot chain analysis: no signature/public key provided — status=unknown"
        )
        return BootChainResult(
            status="unknown",
            firmware_hash=firmware_hash,
            detail="No signature or public key supplied — cannot verify.",
        )

    try:
        valid = verify_ed25519(public_key_bytes, signature, firmware_bytes)
    except Exception as e:
        logger.warning(f"Boot chain analysis: malformed key/signature input — {e}")
        return BootChainResult(
            status="unknown",
            firmware_hash=firmware_hash,
            detail=f"Malformed signature or key: {e}",
        )

    if valid:
        logger.info("Boot chain analysis: signature valid")
        return BootChainResult(
            status="valid",
            firmware_hash=firmware_hash,
            detail="Signature verified against provided public key.",
        )

    logger.warning("Boot chain analysis: signature INVALID")
    return BootChainResult(
        status="invalid",
        firmware_hash=firmware_hash,
        detail="Signature does not match firmware under provided public key.",
    )
