from __future__ import annotations

from typing import Any

from firmware.parser import FirmwareParser
from firmware.metadata import FirmwareMetadata, FirmwareMetadataStore
from firmware.compatibility import CompatibilityChecker
from core.logger import get_logger

logger = get_logger(__name__)


class EpsilonFirmwareIntelligence:
    """Epsilon firmware understanding engine.

    Reasons about firmware structures — never modifies them.
    """

    def __init__(self) -> None:
        self._parser = FirmwareParser()
        self._metadata_store = FirmwareMetadataStore()
        self._compatibility = CompatibilityChecker()

    def summarize(self, metadata: dict) -> dict[str, Any]:
        return {
            "format": metadata.get("format", "unknown"),
            "partitions": metadata.get("partitions", []),
            "boot_chain": metadata.get("boot_chain", "unknown"),
            "compatibility": metadata.get("compatibility", "unknown"),
        }

    def parse(self, data: bytes) -> dict[str, Any]:
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError("firmware data must be bytes-like")
        fw_format = self._parser.parse_format(data)
        boot_chain = self._parser.analyze_boot_chain(data)
        partition_table = self._parser.get_partition_table(data)
        return {
            "format": fw_format,
            "boot_chain": boot_chain,
            "partition_table": partition_table.to_dict(),
        }

    def extract_metadata(self, data: bytes) -> dict[str, Any]:
        metadata = self._parser.extract_metadata(data)
        firmware_id = self._metadata_store.store(metadata)
        return {
            "firmware_id": firmware_id,
            **metadata.to_dict(),
        }

    def check_compatibility(self, firmware_metadata: FirmwareMetadata, hardware_model: str) -> dict[str, Any]:
        compatible = self._compatibility.is_compatible(firmware_metadata, hardware_model)
        warnings = self._compatibility.get_warnings(firmware_metadata, hardware_model)
        return {
            "compatible": compatible,
            "warnings": warnings,
        }
