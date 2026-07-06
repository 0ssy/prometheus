from __future__ import annotations


class FirmwareKnowledge:
    def summarize(self, metadata: dict) -> dict:
        return {
            "format": metadata.get("format", "unknown"),
            "partitions": metadata.get("partitions", []),
            "boot_chain": metadata.get("boot_chain", "unknown"),
            "compatibility": metadata.get("compatibility", "unknown"),
        }
