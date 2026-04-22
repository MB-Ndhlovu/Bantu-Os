"""User identity store for Bantu-OS multi-user support."""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .password import generate_api_key, hash_password, verify_password

# ─── Dataclasses ─────────────────────────────────────────────────────────────


@dataclass
class User:
    username: str
    created_at: float = field(default_factory=time.time)
    last_login: float = field(default_factory=time.time)
    api_key_hash: str = ""
    api_key_salt: str = ""
    is_admin: bool = False
    is_active: bool = True
    suspended: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.username,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "suspended": self.suspended,
            "metadata": self.metadata,
        }


# ─── UserStore ─────────────────────────────────────────────────────────────────


class UserStore:
    """Persistent JSON-backed user directory.

    Stores users in a JSON file. Passwords are hashed with salt (100k rounds SHA-256).
    API keys are stored as (hash, salt) pairs.

    Usage:
        store = UserStore()
        store.create_user("alice", "hunter2")
        if store.verify_password("alice", "hunter2"):
            print("welcome")
    """

    VERSION = 1

    def __init__(
        self,
        path: str = "/home/workspace/bantu_os/data/users.json",
    ) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = secrets
        self._load()

    # ─── Persistence ─────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load users from JSON file, create if absent."""
        if self._path.exists():
            data = json.loads(self._path.read_text())
            self._version = data.get("_version", 0)
            self._users = {u["username"]: u for u in data.get("users", [])}
            self._api_keys = data.get("api_keys", {})
        else:
            self._version = self.VERSION
            self._users = {}
            self._api_keys = {}

    def _save(self) -> None:
        """Write users to JSON file atomically."""
        data = {
            "_version": self._version,
            "users": list(self._users.values()),
            "api_keys": self._api_keys,
        }
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self._path)

    # ─── CRUD ───────────────────────────────────────────────────────────────────

    def create_user(
        self,
        username: str,
        password: str,
        *,
        is_admin: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> User:
        """Create a new user. Raises ValueError if username exists."""
        username = username.lower().strip()
        if not username or len(username) < 2:
            raise ValueError("Username must be at least 2 characters")
        if username in self._users:
            raise ValueError(f"User already exists: {username!r}")

        pwd_hash, pwd_salt = hash_password(password)
        user_dict = {
            "username": username,
            "created_at": time.time(),
            "last_login": time.time(),
            "is_admin": is_admin,
            "is_active": True,
            "suspended": False,
            "metadata": metadata or {},
            "api_key_hash": pwd_hash,
            "api_key_salt": pwd_salt,
        }
        self._users[username] = user_dict
        self._save()
        return User(**user_dict)

    def get_user(self, username: str) -> User | None:
        """Return User or None."""
        d = self._users.get(username.lower().strip())
        if d is None:
            return None
        return User(**d)

    def list_users(self) -> list[User]:
        """Return all users."""
        return [User(**d) for d in self._users.values()]

    def delete_user(self, username: str) -> bool:
        """Delete a user. Returns True if deleted."""
        key = username.lower().strip()
        if key not in self._users:
            return False
        del self._users[key]
        self._api_keys = {k: v for k, v in self._api_keys.items() if v != key}
        self._save()
        return True

    # ─── Auth ───────────────────────────────────────────────────────────────────

    def verify_password(self, username: str, password: str) -> bool:
        """Verify username + password. Returns True if correct."""
        user = self.get_user(username)
        if user is None or user.suspended:
            return False
        return verify_password(password, user.api_key_hash, user.api_key_salt)

    def verify_api_key(self, api_key: str) -> User | None:
        """Verify an API key. Returns User or None."""
        if api_key not in self._api_keys:
            return None
        username = self._api_keys[api_key]
        user = self.get_user(username)
        if user is None or user.suspended:
            return None
        return user

    def set_password(self, username: str, password: str) -> None:
        """Change a user's password."""
        user = self.get_user(username)
        if user is None:
            raise ValueError(f"User not found: {username!r}")
        user.api_key_hash, user.api_key_salt = hash_password(password)
        self._users[user.username] = user.to_dict()
        self._save()

    def update_last_login(self, username: str) -> None:
        """Update last_login timestamp."""
        user = self.get_user(username)
        if user is None:
            return
        user.last_login = time.time()
        self._users[user.username] = user.to_dict()
        self._save()

    def suspend_user(self, username: str) -> bool:
        """Suspend a user. Returns True if suspended."""
        user = self.get_user(username)
        if user is None or user.is_admin:
            return False
        user.suspended = True
        self._users[user.username] = user.to_dict()
        self._save()
        return True

    def reactivate_user(self, username: str) -> bool:
        """Reactivate a suspended user."""
        user = self.get_user(username)
        if user is None:
            return False
        user.suspended = False
        self._users[user.username] = user.to_dict()
        self._save()
        return True

    def create_api_key(self, username: str) -> tuple[str, str]:
        """Generate an API key for a user. Returns (api_key, hint)."""
        user = self.get_user(username)
        if user is None:
            raise ValueError(f"User not found: {username!r}")
        api_key = generate_api_key()
        self._api_keys[api_key] = user.username
        user.last_login = time.time()
        self._users[user.username] = user.to_dict()
        self._save()
        return api_key, "btu_..."

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key. Returns True if revoked."""
        if api_key not in self._api_keys:
            return False
        del self._api_keys[api_key]
        self._save()
        return True
