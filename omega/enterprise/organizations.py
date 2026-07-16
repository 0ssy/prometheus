from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import threading
import uuid

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Organization:
    org_id: str
    name: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


class OrganizationRegistry:
    def __init__(self) -> None:
        self._orgs: dict[str, Organization] = {}
        self._lock = threading.RLock()

    def create(self, name: str, metadata: dict[str, Any] | None = None) -> Organization:
        org_id = str(uuid.uuid4())
        org = Organization(org_id=org_id, name=name, metadata=metadata or {})
        with self._lock:
            self._orgs[org_id] = org
        return org

    def get(self, org_id: str) -> Organization | None:
        with self._lock:
            return self._orgs.get(org_id)

    def list_all(self) -> list[Organization]:
        with self._lock:
            return list(self._orgs.values())

    def update(self, org_id: str, name: str | None = None, metadata: dict[str, Any] | None = None) -> Organization:
        with self._lock:
            org = self._orgs.get(org_id)
            if org is None:
                raise RuntimeError(f"Organization not found: {org_id}")
            if name is not None:
                org.name = name
            if metadata is not None:
                org.metadata = metadata
            return org
