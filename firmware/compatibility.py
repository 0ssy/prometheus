from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional

from core.logger import get_logger

from .metadata import FirmwareMetadata

logger = get_logger(__name__)


@dataclass
class CompatibilityEntry:
    firmware_format: str
    hardware_model: str
    firmware_version: str
    compatible: bool
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CompatibilityMatrix:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str, str], CompatibilityEntry] = {}

    def register(
        self,
        firmware_format: str,
        hardware_model: str,
        firmware_version: str,
        compatible: bool,
        notes: str,
    ) -> None:
        if not firmware_format or not hardware_model or not firmware_version:
            raise ValueError(
                "firmware_format, hardware_model and firmware_version are required"
            )
        key = (firmware_format.lower(), hardware_model.lower(), firmware_version.lower())
        entry = CompatibilityEntry(
            firmware_format=firmware_format,
            hardware_model=hardware_model,
            firmware_version=firmware_version,
            compatible=compatible,
            notes=notes,
        )
        self._entries[key] = entry
        logger.info(
            "Registered compatibility %s/%s/%s compatible=%s",
            firmware_format,
            hardware_model,
            firmware_version,
            compatible,
        )

    def check(
        self,
        firmware_format: str,
        hardware_model: str,
        firmware_version: str,
    ) -> dict[str, Any]:
        key = (firmware_format.lower(), hardware_model.lower(), firmware_version.lower())
        entry = self._entries.get(key)
        if entry is None:
            return {
                "compatible": False,
                "known": False,
                "notes": "No compatibility record found",
            }
        return {
            "compatible": entry.compatible,
            "known": True,
            "notes": entry.notes,
        }

    def list_compatible(
        self,
        firmware_format: str,
        hardware_model: str,
    ) -> list[dict[str, Any]]:
        result = []
        for entry in self._entries.values():
            if (
                entry.firmware_format.lower() == firmware_format.lower()
                and entry.hardware_model.lower() == hardware_model.lower()
                and entry.compatible
            ):
                result.append(entry.to_dict())
        return result


class CompatibilityChecker:
    def __init__(self, matrix: Optional[CompatibilityMatrix] = None) -> None:
        self._matrix = matrix or CompatibilityMatrix()

    def is_compatible(
        self,
        firmware_metadata: FirmwareMetadata,
        hardware_model: str,
    ) -> bool:
        if not isinstance(firmware_metadata, FirmwareMetadata):
            raise ValueError("firmware_metadata must be a FirmwareMetadata instance")
        result = self._matrix.check(
            firmware_metadata.format,
            hardware_model,
            firmware_metadata.version,
        )
        return bool(result.get("compatible", False))

    def get_warnings(
        self,
        firmware_metadata: FirmwareMetadata,
        hardware_model: str,
    ) -> list[str]:
        if not isinstance(firmware_metadata, FirmwareMetadata):
            raise ValueError("firmware_metadata must be a FirmwareMetadata instance")
        result = self._matrix.check(
            firmware_metadata.format,
            hardware_model,
            firmware_metadata.version,
        )
        warnings: list[str] = []
        if not result.get("known", False):
            warnings.append(
                f"No compatibility record for {firmware_metadata.format} "
                f"{firmware_metadata.version} on {hardware_model}"
            )
        elif not result.get("compatible", False):
            warnings.append(
                f"Incompatible: {result.get('notes', 'no details')}"
            )
        if not firmware_metadata.signature:
            warnings.append("Firmware is unsigned")
        if firmware_metadata.size_bytes <= 0:
            warnings.append("Reported firmware size is invalid")
        return warnings
