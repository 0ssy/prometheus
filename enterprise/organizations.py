from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
import uuid

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Organization:
    org_id: str
    name: str
    created_at: datetime
    metadata: dict = field(default_factory=dict)


class OrganizationRegistry:
    def __init__(self) -> None:
        self._orgs: dict[str, Organization] = {}
        self._lock = threading.RLock()

    def create(self, name: str, metadata: dict | None = None) -> Organization:
        org = Organization(
            org_id=f"org_{uuid.uuid4().hex[:12]}",
            name=name,
            created_at=datetime.now(timezone.utc),
            metadata=dict(metadata) if metadata else {},
        )
        with self._lock:
            self._orgs[org.org_id] = org
        logger.info(f"Created organization: {org.org_id} ({name})")
        return org

    def get(self, org_id: str) -> Organization | None:
        with self._lock:
            return self._orgs.get(org_id)

    def list_all(self) -> list[Organization]:
        with self._lock:
            return list(self._orgs.values())

    def update(
        self, org_id: str, name: str | None = None, metadata: dict | None = None
    ) -> Organization:
        with self._lock:
            org = self._orgs.get(org_id)
            if org is None:
                raise KeyError(f"Organization not found: {org_id}")
            if name is not None:
                org.name = name
            if metadata is not None:
                org.metadata.update(metadata)
            logger.info(f"Updated organization: {org_id}")
            return org
