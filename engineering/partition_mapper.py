"""
Prometheus Partition Mapper (RFC 0002, Phase Gamma)
-----------------------------------------
Reads a GPT partition table from a raw disk path or disk image file.

READ-ONLY. This module never writes to a disk, ever — there is no write
path in this file at all, by design, not just by convention.

Every call requires the caller to pass ownership_declared=True explicitly.
There is no default that lets this run silently against an undeclared
target — see RFC 0000 and RFC 0002's binding scope statement. This is the
same "declared, not verified" honesty as devices/ownership.py: it stops
you from calling it by accident, it does not cryptographically verify you
actually own the disk.

MBR-only disks are reported as scheme="mbr" with no partitions parsed —
full MBR partition parsing is a small, separate addition, not built here
to keep this module's first version focused on GPT (the modern default on
anything you're likely to test against in 2026).
"""

import struct
from dataclasses import dataclass, field, asdict
from core.logger import get_logger

logger = get_logger(__name__)

GPT_SIGNATURE = b"EFI PART"


class OwnershipNotDeclaredError(PermissionError):
    pass


@dataclass
class PartitionEntry:
    index: int
    type_guid: str
    unique_guid: str
    first_lba: int
    last_lba: int
    name: str
    size_bytes: int


@dataclass
class PartitionTable:
    disk_path: str
    scheme: str  # "gpt" | "mbr" | "unknown"
    sector_size: int
    partitions: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _read_sectors(path: str, start_lba: int, count: int, sector_size: int) -> bytes:
    with open(path, "rb") as f:
        f.seek(start_lba * sector_size)
        data = f.read(count * sector_size)
    return data


def _format_guid(raw: bytes) -> str:
    # GPT GUIDs are mixed-endian: first three fields little-endian, last two big-endian
    d1, d2, d3 = struct.unpack("<IHH", raw[0:8])
    d4 = raw[8:10].hex()
    d5 = raw[10:16].hex()
    return f"{d1:08x}-{d2:04x}-{d3:04x}-{d4}-{d5}"


def read_partition_table(
    disk_path: str, ownership_declared: bool, sector_size: int = 512
) -> PartitionTable:
    if not ownership_declared:
        logger.warning(f"Blocked partition read on {disk_path}: ownership not declared")
        raise OwnershipNotDeclaredError(
            f"Refusing to read {disk_path}: ownership_declared must be explicitly True. "
            f"This module only inspects disks you own or are enrolled to inspect."
        )

    mbr = _read_sectors(disk_path, 0, 1, sector_size)
    is_gpt = mbr[0x1C2] == 0xEE  # protective MBR partition type byte

    if not is_gpt:
        logger.info(
            f"{disk_path}: no GPT protective MBR found — reporting as scheme=mbr"
        )
        return PartitionTable(
            disk_path=disk_path, scheme="mbr", sector_size=sector_size
        )

    gpt_header = _read_sectors(disk_path, 1, 1, sector_size)
    if gpt_header[0:8] != GPT_SIGNATURE:
        logger.warning(
            f"{disk_path}: protective MBR present but GPT signature missing/corrupt"
        )
        return PartitionTable(
            disk_path=disk_path, scheme="unknown", sector_size=sector_size
        )

    partition_entry_lba = struct.unpack("<Q", gpt_header[72:80])[0]
    num_entries = struct.unpack("<I", gpt_header[80:84])[0]
    entry_size = struct.unpack("<I", gpt_header[84:88])[0]

    entries_bytes_needed = num_entries * entry_size
    sectors_needed = (entries_bytes_needed + sector_size - 1) // sector_size
    raw_entries = _read_sectors(
        disk_path, partition_entry_lba, sectors_needed, sector_size
    )

    partitions = []
    for i in range(num_entries):
        entry = raw_entries[i * entry_size : i * entry_size + entry_size]
        if len(entry) < 128:
            break
        type_guid_raw = entry[0:16]
        if type_guid_raw == b"\x00" * 16:
            continue  # unused entry slot
        unique_guid_raw = entry[16:32]
        first_lba, last_lba = struct.unpack("<QQ", entry[32:48])
        name_raw = entry[56:128]
        name = name_raw.decode("utf-16-le", errors="ignore").rstrip("\x00")

        partitions.append(
            PartitionEntry(
                index=i,
                type_guid=_format_guid(type_guid_raw),
                unique_guid=_format_guid(unique_guid_raw),
                first_lba=first_lba,
                last_lba=last_lba,
                name=name,
                size_bytes=(last_lba - first_lba + 1) * sector_size,
            )
        )

    logger.info(f"{disk_path}: parsed GPT table, {len(partitions)} partitions found")
    return PartitionTable(
        disk_path=disk_path,
        scheme="gpt",
        sector_size=sector_size,
        partitions=partitions,
    )
