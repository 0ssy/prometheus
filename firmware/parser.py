from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any

from core.logger import get_logger

from .metadata import FirmwareMetadata, FirmwareMetadataStore, compute_sha256
from .partitions import PartitionParser, PartitionTable, PartitionMapper
from .compatibility import CompatibilityMatrix, CompatibilityChecker

logger = get_logger(__name__)


@dataclass
class BootChainInfo:
    bootloader: str
    verified: bool
    signature_valid: bool
    chain_length: int
    stages: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FirmwareParser:
    KNOWN_FORMATS = ("uefi", "uboot", "android_ab", "raw", "fit")

    def __init__(self) -> None:
        self._metadata_store = FirmwareMetadataStore()
        self._partition_mapper = PartitionMapper()

    def parse_format(self, data: bytes) -> str:
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError("data must be bytes-like")
        if len(data) == 0:
            raise ValueError("data is empty")

        scheme = PartitionParser.detect_scheme(data)
        if scheme == "gpt":
            return "uefi"
        if scheme == "mbr":
            return "uboot"

        if data[:4] == b"ANDD":
            return "android_ab"
        if data[:3] == b"FIT":
            return "fit"

        logger.info("Could not detect structured format; reporting raw")
        return "raw"

    def extract_metadata(self, data: bytes) -> FirmwareMetadata:
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError("data must be bytes-like")
        if len(data) == 0:
            raise ValueError("data is empty")

        fw_format = self.parse_format(data)
        digest = compute_sha256(data)

        metadata = FirmwareMetadata(
            format=fw_format,
            version="0.0.0-simulated",
            vendor="unknown",
            build_date="1970-01-01T00:00:00Z",
            size_bytes=len(data),
            hash_sha256=digest,
            signature=None,
            public_key_id=None,
        )
        logger.info(
            "Extracted simulated metadata format=%s size=%d",
            fw_format,
            len(data),
        )
        return metadata

    def analyze_boot_chain(self, data: bytes) -> dict[str, Any]:
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError("data must be bytes-like")

        fw_format = self.parse_format(data)
        if fw_format == "uefi":
            info = BootChainInfo(
                bootloader="shim",
                verified=True,
                signature_valid=False,
                chain_length=3,
                stages=["shim", "grub", "kernel"],
            )
        elif fw_format == "uboot":
            info = BootChainInfo(
                bootloader="u-boot",
                verified=False,
                signature_valid=False,
                chain_length=2,
                stages=["spl", "u-boot", "kernel"],
            )
        elif fw_format == "android_ab":
            info = BootChainInfo(
                bootloader="aboot",
                verified=True,
                signature_valid=True,
                chain_length=3,
                stages=["aboot", "bootloader", "kernel"],
            )
        else:
            info = BootChainInfo(
                bootloader="unknown",
                verified=False,
                signature_valid=False,
                chain_length=1,
                stages=["kernel"],
            )

        logger.info("Analyzed boot chain format=%s chain_length=%d", fw_format, info.chain_length)
        return info.to_dict()

    def get_partition_table(self, data: bytes) -> PartitionTable:
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError("data must be bytes-like")

        scheme = PartitionParser.detect_scheme(data)
        if scheme == "gpt":
            return PartitionParser.parse_gpt(data)
        if scheme == "mbr":
            return PartitionParser.parse_mbr(data)

        raise RuntimeError("No recognizable partition scheme in firmware blob")
