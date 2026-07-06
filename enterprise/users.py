from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
import uuid

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class User:
    user_id: str
    email: str
    name: str
    org_id: str
    team_ids: set = field(default_factory=set)
    roles: set = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: datetime | None = None


class UserRegistry:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._by_email: dict[str, str] = {}
        self._lock = threading.RLock()

    def create(
        self,
        email: str,
        name: str,
        org_id: str,
        team_ids: set | None = None,
        roles: set | None = None,
    ) -> User:
        user = User(
            user_id=f"user_{uuid.uuid4().hex[:12]}",
            email=email,
            name=name,
            org_id=org_id,
            team_ids=set(team_ids) if team_ids else set(),
            roles=set(roles) if roles else set(),
        )
        with self._lock:
            self._users[user.user_id] = user
            self._by_email[email] = user.user_id
        logger.info(f"Created user: {user.user_id} ({email})")
        return user

    def get(self, user_id: str) -> User | None:
        with self._lock:
            return self._users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        with self._lock:
            user_id = self._by_email.get(email)
            return self._users.get(user_id) if user_id else None

    def list_by_org(self, org_id: str) -> list[User]:
        with self._lock:
            return [u for u in self._users.values() if u.org_id == org_id]

    def list_by_team(self, team_id: str) -> list[User]:
        with self._lock:
            return [u for u in self._users.values() if team_id in u.team_ids]

    def add_role(self, user_id: str, role: str) -> None:
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                raise KeyError(f"User not found: {user_id}")
            user.roles.add(role)
            logger.info(f"Added role {role!r} to user: {user_id}")

    def remove_role(self, user_id: str, role: str) -> None:
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                raise KeyError(f"User not found: {user_id}")
            user.roles.discard(role)
            logger.info(f"Removed role {role!r} from user: {user_id}")
