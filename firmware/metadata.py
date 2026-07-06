from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, asdict
from typing import Any, Optional

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FirmwareMetadata:
    format: str
    version: str
    vendor: str
    build_date: str
    size_bytes: int
    hash_sha256: str
    signature: Optional[str] = None
    public_key_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FirmwareMetadataStore:
    def __init__(self) -> None:
        self._store: dict[str, FirmwareMetadata] = {}

    def store(self, metadata: FirmwareMetadata) -> str:
        if not isinstance(metadata, FirmwareMetadata):
            raise ValueError("metadata must be a FirmwareMetadata instance")
        if not metadata.hash_sha256:
            raise ValueError("metadata.hash_sha256 is required")

        firmware_id = uuid.uuid4().hex
        self._store[firmware_id] = metadata
        logger.info(
            "Stored firmware metadata id=%s vendor=%s version=%s",
            firmware_id,
            metadata.vendor,
            metadata.version,
        )
        return firmware_id

    def get(self, firmware_id: str) -> FirmwareMetadata:
        metadata = self._store.get(firmware_id)
        if metadata is None:
            raise RuntimeError(f"No firmware metadata for id: {firmware_id}")
        return metadata

    def list_all(self) -> list[FirmwareMetadata]:
        return list(self._store.values())

    def search_by_vendor(self, vendor: str) -> list[FirmwareMetadata]:
        return [
            m
            for m in self._store.values()
            if m.vendor.lower() == vendor.lower()
        ]

    def search_by_format(self, format: str) -> list[FirmwareMetadata]:
        return [
            m
            for m in self._store.values()
            if m.format.lower() == format.lower()
        ]


def compute_sha256(data: bytes) -> str:
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("data must be bytes-like")
    return hashlib.sha256(data).hexdigest()
