"""
Memory consolidation (RC8 AI Runtime Expansion).

Moves short-term memories into long-term storage, mirroring the way the
platform separates transient working memory from durable knowledge. The
current implementation is a stub that leaves persistence to a future
backend while keeping the memory/reasoning/db wiring in place.
"""

from __future__ import annotations

from core.logger import get_logger

logger = get_logger(__name__)


class MemoryConsolidator:
    def consolidate(self, memory_api, reasoning_api, db) -> dict:
        return {"consolidated": 0, "status": "stub"}

    def promote_to_long_term(self, memory_id: str, reasoning_api, db) -> dict:
        return {"memory_id": memory_id, "status": "stub"}
