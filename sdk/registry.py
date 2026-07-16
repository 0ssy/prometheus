"""
P9 Prometheus SDK — versioning + compatibility policy.

Semver compatibility matrix: major = breaking, minor = additive,
patch = fix. A published SDK version records the compatibility floor
it targets; the matrix can answer whether two published versions are
compatible.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from core.logger import get_logger
from sqlalchemy.orm import Session

from sdk.models import SdkVersion

logger = get_logger(__name__)


def _parse(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid semver: {version}")
    return tuple(int(p) for p in parts)  # type: ignore[misc]


def is_compatible(a: str, b: str) -> bool:
    """Two SDK versions are compatible if same major and a's minor/patch
    is not ahead of b's (additive compatibility)."""
    ma, mia, pa = _parse(a)
    mb, mib, pb = _parse(b)
    if ma != mb:
        return False
    return (mia, pa) <= (mib, pb)


@dataclass
class PublishedSdk:
    language: str
    version: str
    compatibility_target: str


class SdkRegistry:
    def publish(self, db: Session, sdk: PublishedSdk) -> SdkVersion:
        row = SdkVersion(
            id=str(uuid.uuid4()),
            language=sdk.language,
            version=sdk.version,
            compatibility_target=sdk.compatibility_target,
            published_at=datetime.now(timezone.utc),
        )
        db.add(row)
        db.commit()
        return row

    def list_for_language(self, db: Session, language: str) -> list[SdkVersion]:
        return (
            db.query(SdkVersion)
            .filter(SdkVersion.language == language)
            .order_by(SdkVersion.published_at.desc())
            .all()
        )

    def compatible(self, db: Session, language: str, version: str) -> list[SdkVersion]:
        return [v for v in self.list_for_language(db, language) if is_compatible(v.version, version)]
