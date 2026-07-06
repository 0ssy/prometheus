from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
import uuid

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Project:
    project_id: str
    org_id: str
    name: str
    description: str
    created_at: datetime
    settings: dict = field(default_factory=dict)


class ProjectRegistry:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._lock = threading.RLock()

    def create(
        self,
        org_id: str,
        name: str,
        description: str = "",
        settings: dict | None = None,
    ) -> Project:
        project = Project(
            project_id=f"proj_{uuid.uuid4().hex[:12]}",
            org_id=org_id,
            name=name,
            description=description,
            created_at=datetime.now(timezone.utc),
            settings=dict(settings) if settings else {},
        )
        with self._lock:
            self._projects[project.project_id] = project
        logger.info(f"Created project: {project.project_id} ({name})")
        return project

    def get(self, project_id: str) -> Project | None:
        with self._lock:
            return self._projects.get(project_id)

    def list_by_org(self, org_id: str) -> list[Project]:
        with self._lock:
            return [p for p in self._projects.values() if p.org_id == org_id]

    def update(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        settings: dict | None = None,
    ) -> Project:
        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                raise KeyError(f"Project not found: {project_id}")
            if name is not None:
                project.name = name
            if description is not None:
                project.description = description
            if settings is not None:
                project.settings.update(settings)
            logger.info(f"Updated project: {project_id}")
            return project
