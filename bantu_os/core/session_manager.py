"""
Bantu-OS Multi-User Session Manager — Phase 3+4

Enables multiple concurrent AI sessions, each with:
- Own isolated memory vector store
- Own conversation history
- Own per-user token budget
- Per-user tool permissions
- Clean session teardown

Usage:
    from bantu_os.core.session_manager import SessionManager, UserSession

    mgr = SessionManager()
    session = await mgr.create_session("alice")
    result = await session.run("list my files")
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..memory import Memory
from ..memory.knowledge_graph import KnowledgeGraph
from ..memory.vector_db import VectorDB
from .kernel import Kernel

# ─── Exceptions ───────────────────────────────────────────────────────────────


class SessionError(Exception):
    """Base exception for session errors."""

    pass


class SessionNotFoundError(SessionError):
    """Raised when a session ID does not exist."""

    pass


class BudgetExceededError(SessionError):
    """Raised when a user's token budget is exhausted."""

    pass


# ─── Budget tracker ────────────────────────────────────────────────────────


@dataclass
class TokenBudget:
    """Per-user token spending limits."""

    max_tokens_per_session: int = 100_000
    max_tokens_per_request: int = 8_192
    warn_threshold: float = 0.80

    _spent: int = field(default=0, repr=False)
    _last_warning_at: float = field(default=0.0, repr=False)

    @property
    def spent(self) -> int:
        return self._spent

    @property
    def remaining(self) -> int:
        return max(0, self.max_tokens_per_session - self._spent)

    def can_spend(self, tokens: int) -> bool:
        return (
            tokens <= self.max_tokens_per_request
            and (self._spent + tokens) <= self.max_tokens_per_session
        )

    def record(self, tokens: int) -> bool:
        self._spent += tokens
        usage = self._spent / self.max_tokens_per_session
        if usage >= self.warn_threshold and (time.time() - self._last_warning_at) > 60:
            self._last_warning_at = time.time()
            return True
        if self._spent >= self.max_tokens_per_session:
            raise BudgetExceededError(
                f"Session budget exhausted: {self._spent}/{self.max_tokens_per_session} tokens"
            )
        return True

    def reset(self) -> None:
        self._spent = 0
        self._last_warning_at = 0.0


# ─── Tool permission ────────────────────────────────────────────────────────


@dataclass
class ToolPermissions:
    """Per-user tool access flags. Defaults lock down destructive operations."""

    file_read: bool = True
    file_write: bool = True
    file_delete: bool = False
    process_run: bool = False
    process_kill: bool = False
    network_outbound: bool = True
    messaging: bool = True
    fintech: bool = False
    crypto: bool = False
    iot: bool = False
    hardware: bool = False
    admin: bool = False

    def can_use(self, tool_name: str) -> bool:
        if self.admin:
            return True
        _dangerous = {"delete", "kill_process", "kill_pid"}
        if tool_name in _dangerous:
            flag = "file_delete" if "delete" in tool_name else "process_kill"
            return getattr(self, flag, False)
        tool_to_flag = {
            "file": self.file_read,
            "process": self.process_run,
            "network": self.network_outbound,
            "messaging": self.messaging,
            "fintech": self.fintech,
            "crypto": self.crypto,
            "iot": self.iot,
            "hardware": self.hardware,
        }
        for prefix, allowed in tool_to_flag.items():
            if tool_name.startswith(prefix):
                return allowed
        return True

    def grant(self, permission: str) -> None:
        if permission == "file_delete":
            self.file_delete = True
        elif permission == "process_run":
            self.process_run = True
        elif permission == "process_kill":
            self.process_kill = True
        elif permission == "fintech":
            self.fintech = True
        elif permission == "crypto":
            self.crypto = True
        elif permission == "iot":
            self.iot = True
        elif permission == "hardware":
            self.hardware = True
        elif permission == "admin":
            self.admin = True
        else:
            raise ValueError(f"Unknown permission: {permission!r}")

    def revoke(self, permission: str) -> None:
        if permission == "admin":
            self.admin = False
            self.file_delete = False
            self.process_run = False
            self.process_kill = False
            self.fintech = False
            self.crypto = False
            self.iot = False
            self.hardware = False
        elif permission == "file_delete":
            self.file_delete = False
        elif permission == "process_run":
            self.process_run = False
        elif permission == "process_kill":
            self.process_kill = False
        elif permission == "fintech":
            self.fintech = False
        elif permission == "crypto":
            self.crypto = False
        elif permission == "iot":
            self.iot = False
        elif permission == "hardware":
            self.hardware = False


# ─── User session ────────────────────────────────────────────────────────────


@dataclass
class UserSession:
    """Isolated AI session for one user."""

    session_id: str
    username: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    request_count: int = 0

    _kernel: Optional[Kernel] = None
    _memory: Optional[Memory] = None
    _budget: TokenBudget = field(default_factory=TokenBudget)
    _permissions: ToolPermissions = field(default_factory=ToolPermissions)

    @property
    def kernel(self) -> Kernel:
        if self._kernel is None:
            self._kernel = Kernel()
        return self._kernel

    def set_kernel(self, kernel: Kernel) -> None:
        self._kernel = kernel

    @property
    def memory(self) -> Memory:
        if self._memory is None:
            self._memory = Memory(
                embeddings=None,
                vector_db=VectorDB(),
                knowledge_graph=KnowledgeGraph(),
            )
        return self._memory

    @property
    def budget(self) -> TokenBudget:
        return self._budget

    @property
    def permissions(self) -> ToolPermissions:
        return self._permissions

    def touch(self) -> None:
        self.last_active = time.time()

    async def run(self, text: str) -> str:
        """Run a prompt through the session's kernel with memory context."""
        self.touch()
        self.request_count += 1

        memory_context: List[Dict[str, Any]] = []
        if self._memory is not None:
            try:
                results = await self._memory.retrieve_memory(text, top_k=5)
                if results:
                    snippets = [r.get("text", "") for r in results if r.get("text")]
                    if snippets:
                        memory_context.append(
                            {
                                "role": "system",
                                "content": "Relevant context from memory:\n"
                                + "\n".join(f"- {s}" for s in snippets),
                            }
                        )
            except Exception:
                pass

        try:
            result = await self.kernel.process_input(
                text, context=memory_context or None
            )
            tokens_used = (len(text) + len(result)) // 4
            try:
                self.budget.record(tokens_used)
            except BudgetExceededError:
                return "[Session budget exhausted. Ask the user to reset or increase the budget.]"
            return result
        except BudgetExceededError:
            raise

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "username": self.username,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "request_count": self.request_count,
            "budget_spent": self.budget.spent,
            "budget_max": self.budget.max_tokens_per_session,
            "permissions": {
                "admin": self._permissions.admin,
                "file_delete": self._permissions.file_delete,
                "process_run": self._permissions.process_run,
                "process_kill": self._permissions.process_kill,
                "fintech": self._permissions.fintech,
                "crypto": self._permissions.crypto,
            },
        }


# ─── Session manager ───────────────────────────────────────────────────────


class SessionManager:
    """
    Central multi-user session orchestrator.

    - Creates and tracks isolated UserSession objects
    - Enforces per-session and per-user limits
    - Thread-safe via asyncio.Lock
    """

    MAX_SESSIONS = 64
    SESSION_TTL_SECONDS = 3600

    def __init__(self) -> None:
        self._sessions: Dict[str, UserSession] = {}
        self._username_index: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        username: str,
        kernel: Optional[Kernel] = None,
        budget: Optional[TokenBudget] = None,
        permissions: Optional[ToolPermissions] = None,
    ) -> UserSession:
        """Create a new isolated session for a user."""
        async with self._lock:
            if len(self._sessions) >= self.MAX_SESSIONS:
                raise SessionError(f"Session limit reached ({self.MAX_SESSIONS}).")
            if username in self._username_index:
                existing_id = self._username_index[username]
                if existing_id in self._sessions:
                    return self._sessions[existing_id]
            session_id = f"sess_{username}_{int(time.time() * 1000)}"
            session = UserSession(
                session_id=session_id,
                username=username,
                _kernel=kernel,
                _budget=budget or TokenBudget(),
                _permissions=permissions or ToolPermissions(),
            )
            self._sessions[session_id] = session
            self._username_index[username] = session_id
            return session

    async def get_session(self, session_id: str) -> UserSession:
        if session_id not in self._sessions:
            raise SessionNotFoundError(f"No session: {session_id!r}")
        return self._sessions[session_id]

    async def get_session_by_username(self, username: str) -> UserSession:
        if username not in self._username_index:
            raise SessionNotFoundError(f"No session for user: {username!r}")
        return self._sessions[self._username_index[username]]

    async def destroy_session(self, session_id: str) -> None:
        async with self._lock:
            if session_id in self._sessions:
                session = self._sessions.pop(session_id)
                self._username_index.pop(session.username, None)

    async def destroy_user(self, username: str) -> None:
        async with self._lock:
            if username in self._username_index:
                await self.destroy_session(self._username_index[username])

    async def list_sessions(self) -> List[Dict[str, Any]]:
        async with self._lock:
            return [s.to_dict() for s in self._sessions.values()]

    async def cleanup_stale(self) -> int:
        cutoff = time.time() - self.SESSION_TTL_SECONDS
        removed = 0
        async with self._lock:
            stale = [sid for sid, s in self._sessions.items() if s.last_active < cutoff]
            for sid in stale:
                session = self._sessions.pop(sid)
                self._username_index.pop(session.username, None)
                removed += 1
        return removed

    @property
    def session_count(self) -> int:
        return len(self._sessions)
