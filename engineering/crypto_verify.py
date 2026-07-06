"""
Cryptographic Verification (RFC 0002)
-----------------------------------------
Shared utility other Gamma modules call into for signature/hash
verification — one place that does this, not reimplemented per module,
per RFC 0002's design.

Uses Ed25519, per the project's original tech choices. Verification
only — this module never signs anything on Prometheus's behalf.
"""
import hashlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_ed25519(public_key_bytes: bytes, signature: bytes, data: bytes) -> bool:
    """
    True if signature is valid for data under public_key_bytes.
    Returns False for a bad signature — never raises for that case.
    Raises only on malformed input (wrong key/signature length), which
    is a caller bug, not a verification outcome.
    """
    public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    try:
        public_key.verify(signature, data)
        return True
    except InvalidSignature:
        return False
