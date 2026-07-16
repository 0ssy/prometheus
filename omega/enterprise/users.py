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
    team_ids: set[str] = field(default_factory=set)
    roles: set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: datetime | None = None


class UserRegistry:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._email_index: dict[str, str] = {}
        self._lock = threading.RLock()

    def create(self, email: str, name: str, org_id: str, team_ids: set[str] | None = None, roles: set[str] | None = None) -> User:
        user_id = str(uuid.uuid4())
        user = User(user_id=user_id, email=email, name=name, org_id=org_id, team_ids=team_ids or set(), roles=roles or set())
        with self._lock:
            self._users[user_id] = user
            self._email_index[email.lower()] = user_id
        return user

    def get(self, user_id: str) -> User | None:
        with self._lock:
            return self._users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        with self._lock:
            user_id = self._email_index.get(email.lower())
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
            if user:
                user.roles.add(role)

    def remove_role(self, user_id: str, role: str) -> None:
        with self._lock:
            user = self._users.get(user_id)
            if user:
                user.roles.discard(role)
