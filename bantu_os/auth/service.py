"""Bantu-OS Authentication Service."""

from __future__ import annotations

from .user_store import User, UserStore


class AuthService:
    """Facade for user authentication and API key management."""

    def __init__(self, store_path: str | None = None) -> None:
        self._store = UserStore(store_path=store_path)

    def register_user(
        self, username: str, api_key: str | None = None
    ) -> tuple[bool, str]:
        try:
            key = self._store.add_user(username, api_key=api_key)
            return True, f"User registered: {username} (API key: {key})"
        except ValueError as e:
            return False, str(e)

    def verify_api_key(self, api_key: str) -> User | None:
        return self._store.verify_api_key(api_key)

    def verify_user_password(self, username: str, password: str) -> bool:
        return self._store.verify_password(username, password)

    def remove_user(self, username: str) -> bool:
        return self._store.remove_user(username)

    def list_users(self) -> list[dict]:
        return self._store.list_users()
