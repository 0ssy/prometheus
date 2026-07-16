from __future__ import annotations



from firmware.metadata import FirmwareMetadata, FirmwareMetadataStore, compute_sha256
from firmware.partitions import PartitionParser, PartitionTable, PartitionMapper, Partition
from firmware.compatibility import CompatibilityMatrix, CompatibilityChecker
from firmware.parser import FirmwareParser


GPT_DATA = b"\x00" * 510 + b"\x55\xAA" + b"EFI PART" + b"\x00" * 500
MBR_DATA = b"\x00" * 510 + b"\x55\xAA" + b"\x00" * 500


def test_firmware_metadata_store():
    store = FirmwareMetadataStore()
    metadata = FirmwareMetadata(
        format="uefi",
        version="1.0",
        vendor="acme",
        build_date="2024-01-01T00:00:00Z",
        size_bytes=1024,
        hash_sha256=compute_sha256(b"fake"),
    )
    firmware_id = store.store(metadata)
    retrieved = store.get(firmware_id)
    assert retrieved.vendor == "acme"
    assert len(store.list_all()) == 1


def test_firmware_metadata_search():
    store = FirmwareMetadataStore()
    meta1 = FirmwareMetadata(
        format="uefi", version="1.0", vendor="acme", build_date="2024-01-01T00:00:00Z", size_bytes=1024, hash_sha256=compute_sha256(b"a")
    )
    meta2 = FirmwareMetadata(
        format="uboot", version="2.0", vendor="acme", build_date="2024-01-01T00:00:00Z", size_bytes=2048, hash_sha256=compute_sha256(b"b")
    )
    store.store(meta1)
    store.store(meta2)
    assert len(store.search_by_vendor("acme")) == 2
    assert len(store.search_by_format("uefi")) == 1


def test_partition_parser_detect_scheme():
    assert PartitionParser.detect_scheme(GPT_DATA) == "gpt"
    assert PartitionParser.detect_scheme(MBR_DATA) == "mbr"
    assert PartitionParser.detect_scheme(b"raw") == "unknown"


def test_partition_parser_parse_gpt():
    table = PartitionParser.parse_gpt(GPT_DATA)
    assert table.scheme == "gpt"
    assert table.bootloader_partition == "boot"
    assert len(table.partitions) == 3


def test_partition_parser_parse_mbr():
    table = PartitionParser.parse_mbr(MBR_DATA)
    assert table.scheme == "mbr"
    assert table.bootloader_partition == "primary"
    assert len(table.partitions) == 2


def test_partition_mapper_map_to_paths():
    table = PartitionParser.parse_gpt(GPT_DATA)
    mapper = PartitionMapper()
    mapping = mapper.map_to_paths(table)
    assert mapping["boot"] == "/boot/efi"
    assert mapping["rootfs"] == "/"


def test_partition_mapper_validate_layout():
    table = PartitionParser.parse_gpt(GPT_DATA)
    mapper = PartitionMapper()
    warnings = mapper.validate_layout(table)
    assert warnings == []

    bad_table = PartitionTable(
        scheme="gpt",
        partitions=[
            Partition(name="a", type="t", offset=-1, size=0, flags=[]),
            Partition(name="a", type="t", offset=0, size=1, flags=[]),
        ],
        bootloader_partition="missing",
        total_size=0,
    )
    warnings = mapper.validate_layout(bad_table)
    assert "negative offset" in warnings[0]
    assert "non-positive size" in warnings[1]
    assert "Duplicate partition name" in warnings[2]
    assert "not found in table" in warnings[3]
    assert "total_size is not set" in warnings[4]


def test_compatibility_matrix_register_and_check():
    matrix = CompatibilityMatrix()
    matrix.register("uefi", "model-x", "1.0", True, "fully compatible")
    result = matrix.check("uefi", "model-x", "1.0")
    assert result["compatible"] is True
    assert result["known"] is True
    assert len(matrix.list_compatible("uefi", "model-x")) == 1


def test_compatibility_checker_warnings():
    matrix = CompatibilityMatrix()
    checker = CompatibilityChecker(matrix=matrix)
    metadata = FirmwareMetadata(
        format="uefi", version="1.0", vendor="acme", build_date="2024-01-01T00:00:00Z", size_bytes=1024, hash_sha256="abc"
    )
    warnings = checker.get_warnings(metadata, "model-x")
    assert "No compatibility record" in warnings[0]
    assert "Firmware is unsigned" in warnings[1]
    assert len(warnings) == 2


def test_firmware_parser_parse_format():
    parser = FirmwareParser()
    assert parser.parse_format(GPT_DATA) == "uefi"
    assert parser.parse_format(MBR_DATA) == "uboot"
    assert parser.parse_format(b"\x00" * 100) == "raw"


def test_firmware_parser_extract_metadata():
    parser = FirmwareParser()
    metadata = parser.extract_metadata(GPT_DATA)
    assert metadata.format == "uefi"
    assert metadata.size_bytes == len(GPT_DATA)
    assert metadata.hash_sha256 == compute_sha256(GPT_DATA)


def test_firmware_parser_analyze_boot_chain():
    parser = FirmwareParser()
    gpt_chain = parser.analyze_boot_chain(GPT_DATA)
    assert gpt_chain["bootloader"] == "shim"
    assert gpt_chain["chain_length"] == 3

    mbr_chain = parser.analyze_boot_chain(MBR_DATA)
    assert mbr_chain["bootloader"] == "u-boot"


def test_firmware_parser_get_partition_table():
    parser = FirmwareParser()
    table = parser.get_partition_table(GPT_DATA)
    assert table.scheme == "gpt"
    assert len(table.partitions) == 3
