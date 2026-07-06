from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Partition:
    name: str
    type: str
    offset: int
    size: int
    flags: list[str]
    filesystem: Optional[str] = None
    mount_point: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PartitionTable:
    scheme: str
    partitions: list[Partition]
    bootloader_partition: Optional[str] = None
    total_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "scheme": self.scheme,
            "partitions": [p.to_dict() for p in self.partitions],
            "bootloader_partition": self.bootloader_partition,
            "total_size": self.total_size,
        }


class PartitionParser:
    GPT_SIGNATURE = b"EFI PART"
    MBR_BOOT_SIG = b"\x55\xAA"

    @staticmethod
    def detect_scheme(data: bytes) -> str:
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError("data must be bytes-like")
        if len(data) >= 512 and data[510:512] == PartitionParser.MBR_BOOT_SIG:
            if len(data) >= 512 + 16 and data[512:520] == PartitionParser.GPT_SIGNATURE:
                return "gpt"
            return "mbr"
        return "unknown"

    @staticmethod
    def parse_gpt(data: bytes) -> PartitionTable:
        if PartitionParser.detect_scheme(data) != "gpt":
            raise ValueError("data is not a GPT image")
        logger.info("Simulating GPT parse over %d bytes", len(data))
        partitions = [
            Partition(
                name="boot",
                type="efi_system",
                offset=0x100000,
                size=0x200000,
                flags=["esp", "bootable"],
                filesystem="fat32",
                mount_point="/boot/efi",
            ),
            Partition(
                name="rootfs",
                type="linux_filesystem",
                offset=0x300000,
                size=0x800000,
                flags=["read_only"],
                filesystem="squashfs",
                mount_point="/",
            ),
            Partition(
                name="data",
                type="linux_filesystem",
                offset=0xB00000,
                size=0x400000,
                flags=[],
                filesystem="ext4",
                mount_point="/data",
            ),
        ]
        return PartitionTable(
            scheme="gpt",
            partitions=partitions,
            bootloader_partition="boot",
            total_size=0xF00000,
        )

    @staticmethod
    def parse_mbr(data: bytes) -> PartitionTable:
        if PartitionParser.detect_scheme(data) != "mbr":
            raise ValueError("data is not an MBR image")
        logger.info("Simulating MBR parse over %d bytes", len(data))
        partitions = [
            Partition(
                name="primary",
                type="0x83",
                offset=0x80000,
                size=0x600000,
                flags=["active", "bootable"],
                filesystem="ext4",
                mount_point="/",
            ),
            Partition(
                name="secondary",
                type="0x83",
                offset=0x680000,
                size=0x400000,
                flags=[],
                filesystem="ext4",
                mount_point="/data",
            ),
        ]
        return PartitionTable(
            scheme="mbr",
            partitions=partitions,
            bootloader_partition="primary",
            total_size=0xA80000,
        )


class PartitionMapper:
    def map_to_paths(self, partition_table: PartitionTable) -> dict[str, str]:
        if not isinstance(partition_table, PartitionTable):
            raise ValueError("partition_table must be a PartitionTable instance")
        mapping: dict[str, str] = {}
        for partition in partition_table.partitions:
            if partition.mount_point:
                mapping[partition.name] = partition.mount_point
            else:
                mapping[partition.name] = f"/dev/disk/by-name/{partition.name}"
        return mapping

    def validate_layout(self, partition_table: PartitionTable) -> list[str]:
        if not isinstance(partition_table, PartitionTable):
            raise ValueError("partition_table must be a PartitionTable instance")
        warnings: list[str] = []

        seen_names: dict[str, int] = {}
        for partition in partition_table.partitions:
            if partition.offset < 0:
                warnings.append(f"Partition '{partition.name}' has negative offset")
            if partition.size <= 0:
                warnings.append(f"Partition '{partition.name}' has non-positive size")
            seen_names[partition.name] = seen_names.get(partition.name, 0) + 1

        for name, count in seen_names.items():
            if count > 1:
                warnings.append(f"Duplicate partition name: '{name}' ({count} times)")

        if partition_table.bootloader_partition is None:
            warnings.append("No bootloader partition designated")
        elif not any(
            p.name == partition_table.bootloader_partition
            for p in partition_table.partitions
        ):
            warnings.append(
                f"Bootloader partition '{partition_table.bootloader_partition}' not found in table"
            )

        if partition_table.total_size <= 0:
            warnings.append("Partition table total_size is not set")

        return warnings
