"""Tests for Bantu-OS authentication module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from bantu_os.auth import UserStore, generate_api_key, hash_password, verify_password


class TestPasswordUtils:
    def test_hash_password_deterministic(self) -> None:
        h1, s1 = hash_password("hunter2", salt="abcd")
        h2, s2 = hash_password("hunter2", salt="abcd")
        assert h1 == h2
        assert s1 == s2

    def test_hash_password_different_salts(self) -> None:
        h1, s1 = hash_password("hunter2", salt="aaaa")
        h2, s2 = hash_password("hunter2", salt="bbbb")
        assert h1 != h2

    def test_verify_password_correct(self) -> None:
        h, s = hash_password("secret123")
        assert verify_password("secret123", h, s) is True

    def test_verify_password_wrong(self) -> None:
        h, s = hash_password("secret123")
        assert verify_password("wrongpass", h, s) is False

    def test_generate_api_key_format(self) -> None:
        key = generate_api_key()
        assert key.startswith("btu_")
        assert len(key) > 20

    def test_generate_api_key_unique(self) -> None:
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100


class TestUserStore:
    @pytest.fixture
    def store(self, tmp_path: Path) -> UserStore:
        return UserStore(path=str(tmp_path / "users.json"))

    def test_create_user(self, store: UserStore) -> None:
        store.create_user("alice", "hunter2")
        user = store.get_user("alice")
        assert user is not None
        assert user.username == "alice"
        assert user.is_admin is False
        assert user.suspended is False

    def test_create_user_duplicate(self, store: UserStore) -> None:
        store.create_user("alice", "hunter2")
        with pytest.raises(ValueError, match="already exists"):
            store.create_user("alice", "hunter2")

    def test_create_user_admin(self, store: UserStore) -> None:
        store.create_user("bob", "hunter2", is_admin=True)
        user = store.get_user("bob")
        assert user is not None
        assert user.is_admin is True

    def test_verify_password(self, store: UserStore) -> None:
        store.create_user("alice", "hunter2")
        assert store.verify_password("alice", "hunter2") is True
        assert store.verify_password("alice", "wrong") is False

    def test_verify_password_nonexistent(self, store: UserStore) -> None:
        assert store.verify_password("nobody", "hunter2") is False

    def test_verify_password_suspended(self, store: UserStore) -> None:
        store.create_user("alice", "hunter2")
        store.suspend_user("alice")
        assert store.verify_password("alice", "hunter2") is False

    def test_suspend_and_reactivate(self, store: UserStore) -> None:
        store.create_user("alice", "hunter2")
        assert store.suspend_user("alice") is True
        assert store.get_user("alice").suspended is True
        assert store.reactivate_user("alice") is True
        assert store.get_user("alice").suspended is False

    def test_cannot_suspend_admin(self, store: UserStore) -> None:
        store.create_user("admin", "hunter2", is_admin=True)
        assert store.suspend_user("admin") is False

    def test_delete_user(self, store: UserStore) -> None:
        store.create_user("alice", "hunter2")
        assert store.delete_user("alice") is True
        assert store.get_user("alice") is None
        assert store.delete_user("alice") is False

    def test_create_api_key(self, store: UserStore) -> None:
        store.create_user("alice", "hunter2")
        key, hint = store.create_api_key("alice")
        assert key.startswith("btu_")
        assert hint == "btu_..."
        assert store.verify_api_key(key).username == "alice"

    def test_revoke_api_key(self, store: UserStore) -> None:
        store.create_user("alice", "hunter2")
        key, _ = store.create_api_key("alice")
        assert store.revoke_api_key(key) is True
        assert store.verify_api_key(key) is None

    def test_list_users(self, store: UserStore) -> None:
        store.create_user("alice", "hunter2")
        store.create_user("bob", "hunter2")
        users = store.list_users()
        assert {u.username for u in users} == {"alice", "bob"}

    def test_update_last_login(self, store: UserStore) -> None:
        store.create_user("alice", "hunter2")
        import time
        time.sleep(0.01)
        store.update_last_login("alice")
        user = store.get_user("alice")
        assert user.last_login > 0