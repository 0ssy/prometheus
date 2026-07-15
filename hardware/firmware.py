from __future__ import annotations

from firmware.metadata import FirmwareMetadata, FirmwareMetadataStore, compute_sha256
from firmware.parser import FirmwareParser, BootChainInfo
from firmware.partitions import (
    Partition,
    PartitionTable,
    PartitionParser,
    PartitionMapper,
)
from firmware.compatibility import (
    CompatibilityEntry,
    CompatibilityMatrix,
    CompatibilityChecker,
)

__all__ = [
    "FirmwareMetadata",
    "FirmwareMetadataStore",
    "compute_sha256",
    "FirmwareParser",
    "BootChainInfo",
    "Partition",
    "PartitionTable",
    "PartitionParser",
    "PartitionMapper",
    "CompatibilityEntry",
    "CompatibilityMatrix",
    "CompatibilityChecker",
]
