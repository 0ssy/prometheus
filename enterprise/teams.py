from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
import uuid

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Team:
    team_id: str
    org_id: str
    name: str
    member_ids: set = field(default_factory=set)
    lead_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TeamRegistry:
    def __init__(self) -> None:
        self._teams: dict[str, Team] = {}
        self._lock = threading.RLock()

    def create(self, org_id: str, name: str, lead_id: str | None = None) -> Team:
        team = Team(
            team_id=f"team_{uuid.uuid4().hex[:12]}",
            org_id=org_id,
            name=name,
            lead_id=lead_id,
        )
        with self._lock:
            self._teams[team.team_id] = team
        logger.info(f"Created team: {team.team_id} ({name})")
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
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            team.member_ids.add(user_id)
            logger.info(f"Added member {user_id} to team: {team_id}")

    def remove_member(self, team_id: str, user_id: str) -> None:
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            team.member_ids.discard(user_id)
            if team.lead_id == user_id:
                team.lead_id = None
            logger.info(f"Removed member {user_id} from team: {team_id}")

    def set_lead(self, team_id: str, user_id: str) -> None:
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            team.lead_id = user_id
            team.member_ids.add(user_id)
            logger.info(f"Set lead {user_id} for team: {team_id}")
