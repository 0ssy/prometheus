from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)

_FORMAT_SIGNATURES: dict[bytes, str] = {
    b"\x7fELF": "elf",
    b"UF2\x0a": "uf2",
    b"DfuSe": "dfu",
    b":02000004": "hex",
}


def parse_elf(data: bytes) -> dict[str, Any]:
    return {"format": "elf", "size": len(data), "status": "stub"}


def parse_bin(data: bytes) -> dict[str, Any]:
    return {"format": "bin", "size": len(data), "status": "stub"}


def parse_hex(data: bytes) -> dict[str, Any]:
    return {"format": "hex", "size": len(data), "status": "stub"}


def parse_uf2(data: bytes) -> dict[str, Any]:
    return {"format": "uf2", "size": len(data), "status": "stub"}


def parse_dfu(data: bytes) -> dict[str, Any]:
    return {"format": "dfu", "size": len(data), "status": "stub"}


def detect_format(data: bytes) -> str:
    if not data:
        return "raw"
    for signature, fmt in _FORMAT_SIGNATURES.items():
        if data[: len(signature)] == signature:
            return fmt
    return "raw"
