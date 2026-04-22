"""
Tests for bantu_os.core.session_manager module.
"""

import pytest
import asyncio

from bantu_os.core.session_manager import (
    SessionManager,
    UserSession,
    TokenBudget,
    ToolPermissions,
    SessionError,
    SessionNotFoundError,
    BudgetExceededError,
)


class TestTokenBudget:
    def test_spent_starts_at_zero(self):
        b = TokenBudget()
        assert b.spent == 0
        assert b.remaining == 100_000

    def test_record_increments_spent(self):
        b = TokenBudget(max_tokens_per_session=1000, max_tokens_per_request=500)
        b.record(300)
        assert b.spent == 300
        assert b.remaining == 700

    def test_can_spend_respects_request_cap(self):
        b = TokenBudget(max_tokens_per_session=1000, max_tokens_per_request=200)
        assert b.can_spend(200) is True
        assert b.can_spend(201) is False

    def test_can_spend_respects_session_cap(self):
        b = TokenBudget(max_tokens_per_session=500, max_tokens_per_request=1000)
        b.record(400)
        assert b.can_spend(200) is False

    def test_record_raises_on_exhaustion(self):
        b = TokenBudget(max_tokens_per_session=1000)
        b.record(999)
        with pytest.raises(BudgetExceededError):
            b.record(10)

    def test_reset_clears_spent(self):
        b = TokenBudget()
        b.record(500)
        b.reset()
        assert b.spent == 0
        assert b.remaining == 100_000


class TestToolPermissions:
    def test_admin_bypasses_all(self):
        p = ToolPermissions(admin=True)
        assert p.can_use("crypto_send") is True
        assert p.can_use("fintech_create_payment") is True

    def test_default_blocks_destructive(self):
        p = ToolPermissions()
        assert p.can_use("file_read") is True
        assert p.can_use("delete") is False
        assert p.can_use("kill_process") is False

    def test_grant_unlocks_permission(self):
        p = ToolPermissions()
        p.grant("file_delete")
        assert p.can_use("delete") is True

    def test_revoke_locks_permission(self):
        p = ToolPermissions(file_delete=True)
        p.revoke("file_delete")
        assert p.can_use("delete") is False

    def test_revoke_admin_strips_all(self):
        p = ToolPermissions(admin=True, fintech=True, crypto=True)
        p.revoke("admin")
        assert p.admin is False
        assert p.can_use("fintech_create_payment") is False
        assert p.can_use("crypto_send") is False


class TestUserSession:
    def test_session_created_with_id_and_username(self):
        s = UserSession(session_id="sess_alice_1", username="alice")
        assert s.session_id == "sess_alice_1"
        assert s.username == "alice"
        assert s.request_count == 0

    def test_touch_updates_last_active(self):
        s = UserSession(session_id="sess_alice_1", username="alice")
        old = s.last_active
        s.touch()
        assert s.last_active >= old

    def test_default_kernel_is_initialized(self):
        s = UserSession(session_id="sess_alice_1", username="alice")
        assert s.kernel is not None

    def test_default_budget_is_token_budget(self):
        s = UserSession(session_id="sess_alice_1", username="alice")
        assert isinstance(s.budget, TokenBudget)

    def test_default_permissions_are_tool_permissions(self):
        s = UserSession(session_id="sess_alice_1", username="alice")
        assert isinstance(s.permissions, ToolPermissions)

    def test_to_dict_returns_serializable(self):
        s = UserSession(session_id="sess_alice_1", username="alice")
        d = s.to_dict()
        assert d["session_id"] == "sess_alice_1"
        assert d["username"] == "alice"
        assert d["budget_spent"] == 0
        assert d["permissions"]["admin"] is False


class TestSessionManager:
    def test_create_session_returns_user_session(self):
        mgr = SessionManager()
        session = asyncio.run(mgr.create_session("alice"))
        assert isinstance(session, UserSession)
        assert session.username == "alice"
        assert session.session_id.startswith("sess_alice_")

    def test_create_session_increments_count(self):
        mgr = SessionManager()
        asyncio.run(mgr.create_session("alice"))
        assert mgr.session_count == 1

    def test_get_session_retrieves_session(self):
        mgr = SessionManager()
        created = asyncio.run(mgr.create_session("alice"))
        retrieved = asyncio.run(mgr.get_session(created.session_id))
        assert retrieved.session_id == created.session_id

    def test_get_session_raises_on_unknown(self):
        mgr = SessionManager()
        with pytest.raises(SessionNotFoundError):
            asyncio.run(mgr.get_session("sess_unknown"))

    def test_get_session_by_username(self):
        mgr = SessionManager()
        asyncio.run(mgr.create_session("alice"))
        session = asyncio.run(mgr.get_session_by_username("alice"))
        assert session.username == "alice"

    def test_reuse_session_for_same_username(self):
        mgr = SessionManager()
        s1 = asyncio.run(mgr.create_session("alice"))
        s2 = asyncio.run(mgr.create_session("alice"))
        assert s1.session_id == s2.session_id
        assert mgr.session_count == 1

    def test_destroy_session_removes_session(self):
        mgr = SessionManager()
        s = asyncio.run(mgr.create_session("alice"))
        asyncio.run(mgr.destroy_session(s.session_id))
        assert mgr.session_count == 0

    def test_destroy_user_removes_session(self):
        mgr = SessionManager()
        asyncio.run(mgr.create_session("alice"))
        asyncio.run(mgr.destroy_user("alice"))
        assert mgr.session_count == 0

    def test_list_sessions_returns_all(self):
        mgr = SessionManager()
        asyncio.run(mgr.create_session("alice"))
        asyncio.run(mgr.create_session("bob"))
        sessions = asyncio.run(mgr.list_sessions())
        assert len(sessions) == 2

    def test_max_sessions_enforced(self):
        mgr = SessionManager()
        # Override MAX_SESSIONS for test
        mgr.MAX_SESSIONS = 2
        asyncio.run(mgr.create_session("alice"))
        asyncio.run(mgr.create_session("bob"))
        with pytest.raises(SessionError):
            asyncio.run(mgr.create_session("charlie"))

    def test_cleanup_stale_removes_inactive(self):
        mgr = SessionManager()
        s = asyncio.run(mgr.create_session("alice"))
        # Manually age the session
        s.last_active = 0.0
        removed = asyncio.run(mgr.cleanup_stale())
        assert removed == 1
        assert mgr.session_count == 0
