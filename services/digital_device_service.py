from __future__ import annotations

from sqlalchemy.orm import Session

from contracts.device import DeviceApi
from contracts.memory import MemoryApi
from contracts.reasoning import ReasoningApi
from digital_twin.twin import build_twin


class DigitalDeviceService:
    def __init__(
        self, device_api: DeviceApi, memory_api: MemoryApi, reasoning_api: ReasoningApi
    ):
        self._device_api = device_api
        self._memory_api = memory_api
        self._reasoning_api = reasoning_api

    def build(self, db: Session, device_id: str) -> dict:
        twin = build_twin(db, device_id, device_api=self._device_api).to_dict()
        facts = self._reasoning_api.query_facts(db, subject=device_id)
        memories = self._memory_api.recall(db, tag=device_id, limit=50)
        return {
            "device_id": device_id,
            "state": twin["state"],
            "events": [
                {
                    "predicate": fact.predicate,
                    "object": fact.object,
                    "created_at": fact.created_at.isoformat(),
                }
                for fact in facts
            ],
            "memory": [
                {
                    "id": entry.id,
                    "content": entry.content,
                    "tag": entry.tag,
                    "created_at": entry.created_at.isoformat(),
                }
                for entry in memories
            ],
            "twin": twin,
        }
