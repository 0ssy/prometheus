"""
Firmware Inspector (RFC 0002)
-----------------------------------------
Reads a firmware image from a local file path — a dumped ESP32 .bin,
or any binary blob you want fingerprinted.

READ-ONLY. Reports size and hash always. If the file starts with the
ESP32 image magic byte (0xE9), attempts a best-effort header parse.
Anything else is reported honestly as "unknown_format".
"""
from dataclasses import dataclass, asdict
import struct
from .crypto_verify import sha256_hex
from core.logger import get_logger

logger = get_logger(__name__)

ESP32_MAGIC = 0xE9


@dataclass
class FirmwareReport:
    path: str
    size_bytes: int
    sha256: str
    format: str  # "esp32_image" | "unknown_format"
    details: dict

    def to_dict(self) -> dict:
        return asdict(self)


def inspect_firmware(path: str, ownership_declared: bool) -> FirmwareReport:
    if not ownership_declared:
        logger.warning(f"Blocked firmware inspection on {path}: ownership not declared")
        raise PermissionError(
            f"Refusing to inspect {path}: ownership_declared must be explicitly True."
        )

    with open(path, "rb") as f:
        data = f.read()

    size_bytes = len(data)
    digest = sha256_hex(data)

    if data and data[0] == ESP32_MAGIC and len(data) >= 24:
        segment_count = data[1]
        entry_point = struct.unpack("<I", data[4:8])[0]
        logger.info(f"{path}: recognized as ESP32 image, {segment_count} segment(s)")
        return FirmwareReport(
            path=path, size_bytes=size_bytes, sha256=digest, format="esp32_image",
            details={"segment_count": segment_count, "entry_point": hex(entry_point)},
        )

    logger.info(f"{path}: unrecognized firmware format — reporting hash/size only")
    return FirmwareReport(path=path, size_bytes=size_bytes, sha256=digest, format="unknown_format", details={})
