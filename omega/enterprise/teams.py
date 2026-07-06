from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Team:
    team_id: str
    org_id: str
    name: str
    member_ids: set[str] = field(default_factory=set)
    lead_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TeamRegistry:
    def __init__(self) -> None:
        self._teams: dict[str, Team] = {}
        self._lock = threading.RLock()

    def create(self, org_id: str, name: str, lead_id: str | None = None) -> Team:
        import uuid
        team_id = str(uuid.uuid4())
        team = Team(team_id=team_id, org_id=org_id, name=name, lead_id=lead_id)
        with self._lock:
            self._teams[team_id] = team
        return team

    def get(self, team_id: str) -> Team | None:
        with self._lock:
            return self._teams.get(team_id)

    def list_by_org(self, org_id: str) -> list[Team]:
        with self._lock:
            return [t for t in self._teams.values() if t.org_id == org_id]

    def add_member(self, team_id: str, user_id: str) -> None:
        with self._lock:
            team = self._teams.get(team_id)
            if team:
                team.member_ids.add(user_id)

    def remove_member(self, team_id: str, user_id: str) -> None:
        with self._lock:
            team = self._teams.get(team_id)
            if team:
                team.member_ids.discard(user_id)

    def set_lead(self, team_id: str, user_id: str) -> None:
        with self._lock:
            team = self._teams.get(team_id)
            if team:
                team.lead_id = user_id


import threading
