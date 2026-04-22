"""
Unix socket server for Bantu-OS shell-to-kernel bridge.

Receives JSON commands from the Rust shell and routes them to the Kernel.
Supports two protocols:
  - Unix domain socket  (/tmp/bantu.sock)  — Rust shell connects here
  - TCP socket          (127.0.0.1:18792)  — future multi-client / telnet use

Protocol:
  Send JSON on one line, receive JSON on one line.
  Request (ai):    {"cmd": "ai", "text": "hello"}
  Request (tool):  {"cmd": "tool", "tool": "file", "method": "read", "args": {"path": "/tmp/test.txt"}}
  Request (ping):  {"cmd": "ping"}
  Session commands: {"cmd": "login", "username": "alice"}
                    {"cmd": "logout"}
                    {"cmd": "whoami"}
                    {"cmd": "clear_history"}
                    {"cmd": "session_stats"}
  Response:         {"ok": true,  "result": <str>}
                    {"ok": false, "error":  <str>}
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import socket
import sys
import time
from pathlib import Path
from typing import Optional

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from bantu_os.core.kernel import Kernel
from bantu_os.core.session_manager import (
    BudgetExceededError,
    SessionManager,
    UserSession,
)
from bantu_os.services.file_service import FileService
from bantu_os.services.network_service import NetworkService
from bantu_os.services.process_service import ProcessService

# Phase 2: Messaging, Fintech, Crypto
try:
    from bantu_os.services.crypto import CryptoWalletService
    from bantu_os.services.fintech import FintechService
    from bantu_os.services.messaging import MessagingService

    _PHASE2_AVAILABLE = True
except ImportError:
    _PHASE2_AVAILABLE = False

# Phase 3: IoT, Hardware
try:
    from bantu_os.services.hardware import HardwareService
    from bantu_os.services.iot import IoTService

    _IOT_AVAILABLE = True
    _HARDWARE_AVAILABLE = True
except ImportError:
    _IOT_AVAILABLE = False
    _HARDWARE_AVAILABLE = False


def make_kernel(session: Optional[UserSession] = None) -> Kernel:
    """
    Build a Kernel with all services registered as tools.

    Services are registered as CLASSES (not instances) so each tool call
    instantiates a fresh service object with the caller's kwargs.

    If a session is provided, the Kernel gets session-aware memory injected.
    """
    kernel = Kernel(tools={})

    kernel.register_tool("file", FileService)
    kernel.register_tool("process", ProcessService)
    kernel.register_tool("network", NetworkService)

    # Phase 2: wire messaging, fintech, crypto into the kernel
    if _PHASE2_AVAILABLE:
        kernel.register_tool("messaging", MessagingService)
        kernel.register_tool("fintech", FintechService)
        kernel.register_tool("crypto", CryptoWalletService)

    # Phase 3: wire IoT and Hardware into the kernel
    if _IOT_AVAILABLE:
        kernel.register_tool("iot", IoTService)
    if _HARDWARE_AVAILABLE:
        kernel.register_tool("hardware", HardwareService)

    # Inject session memory if available
    if session is not None and session.memory.embeddings is not None:
        kernel.memory = session.memory
        kernel.memory_top_k = 5

    print(
        "[kernel] Phase 2 services registered: messaging, fintech, crypto"
        if _PHASE2_AVAILABLE
        else "[kernel] Phase 2: not available"
    )
    if _IOT_AVAILABLE or _HARDWARE_AVAILABLE:
        registered = [
            _f
            for _f in [
                ("iot" if _IOT_AVAILABLE else None),
                ("hardware" if _HARDWARE_AVAILABLE else None),
            ]
            if _f
        ]
        print(f"[kernel] Phase 3 services registered: {', '.join(registered)}")

    return kernel


# ---------------------------------------------------------------------------
# Per-client protocol handler
# ---------------------------------------------------------------------------


class ShellProtocol(asyncio.Protocol):
    """
    asyncio Protocol for a line-buffered JSON socket session.

    State machine per connection:
      buffer -> accumulate bytes until '\n' -> decode JSON line -> process -> respond

    Sessions:
      Each connection has an optional session_id. Until the user logs in,
      they get a temporary guest session. After login, all AI requests are
      routed through their persistent UserSession (with memory + history).
    """

    __slots__ = (
        "session_manager",
        "loop",
        "transport",
        "buffer",
        "session_id",
        "_kernel",
        "_session",
    )

    def __init__(
        self,
        session_manager: SessionManager,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.session_manager = session_manager
        self.loop = loop
        self.transport: Optional[asyncio.Transport] = None
        self.buffer: bytearray = bytearray()
        self.session_id: Optional[str] = None
        self._kernel: Optional[Kernel] = None
        self._session: Optional[UserSession] = None

    # ── Kernel lazy-init ─────────────────────────────────────────────────────

    @property
    def kernel(self) -> Kernel:
        if self._kernel is None:
            self._kernel = make_kernel(self._session)
        return self._kernel

    # ── Transport ────────────────────────────────────────────────────────────

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport

    def data_received(self, data: bytes) -> None:
        self.buffer.extend(data)
        while b"\n" in self.buffer:
            line_bytes, self.buffer = self.buffer.split(b"\n", 1)
            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            asyncio.create_task(self._process(line))

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self.transport = None

    # ── Command router ────────────────────────────────────────────────────────

    async def _process(self, line: str) -> None:
        """Parse one JSON line, handle the command, send response."""
        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            await self._send({"ok": False, "error": f"Invalid JSON: {e}"})
            return

        cmd = request.get("cmd", "")

        if cmd == "ping":
            await self._send({"ok": True, "result": "pong"})
            return

        # ── Session commands ────────────────────────────────────────────────

        if cmd == "login":
            username = request.get("username", "").strip()
            if not username:
                await self._send({"ok": False, "error": "username is required"})
                return
            try:
                session = await self.session_manager.create_session(username)
                self.session_id = session.session_id
                self._session = session
                self._kernel = None  # rebuild kernel with session memory
                await self._send(
                    {
                        "ok": True,
                        "result": f"Logged in as {username} (session: {session.session_id})",
                        "session_id": session.session_id,
                    }
                )
            except Exception as e:
                await self._send({"ok": False, "error": str(e)})
            return

        if cmd == "logout":
            if self.session_id:
                await self.session_manager.destroy_session(self.session_id)
            self.session_id = None
            self._session = None
            self._kernel = None
            await self._send({"ok": True, "result": "Logged out."})
            return

        if cmd == "whoami":
            if self._session:
                await self._send(
                    {
                        "ok": True,
                        "result": (
                            f"User: {self._session.username}\n"
                            f"Session: {self._session.session_id}\n"
                            f"Requests: {self._session.request_count}\n"
                            f"Budget: {self._session.budget.spent}/{self._session.budget.max_tokens_per_session} tokens"
                        ),
                        "session_id": self.session_id,
                        "username": self._session.username,
                    }
                )
            else:
                await self._send(
                    {
                        "ok": True,
                        "result": "Guest (not logged in)",
                        "session_id": None,
                        "username": None,
                    }
                )
            return

        if cmd == "clear_history":
            if self._session and self._session._memory is not None:
                try:
                    self._session._memory.clear()
                except Exception:
                    pass
            await self._send({"ok": True, "result": "Conversation history cleared."})
            return

        if cmd == "session_stats":
            stats = await self.session_manager.list_sessions()
            active = [s for s in stats if time.time() - s["last_active"] < 300]
            await self._send(
                {
                    "ok": True,
                    "result": (
                        f"Total sessions: {len(stats)}\n"
                        f"Active (5m): {len(active)}\n"
                        f"Sample: {stats[0]['username'] if stats else 'none'}"
                    ),
                    "sessions": stats,
                }
            )
            return

        # ── AI command ──────────────────────────────────────────────────────

        if cmd == "ai":
            text = request.get("text", "")
            if not text:
                await self._send({"ok": False, "error": "text is required"})
                return

            try:
                if self._session:
                    # Route through session for persistent context
                    result = await self._session.run(text)
                else:
                    # Guest — no session, just kernel
                    result = await self.kernel.process_input(text)
                await self._send({"ok": True, "result": result})
            except BudgetExceededError:
                await self._send(
                    {
                        "ok": False,
                        "error": "Session token budget exhausted. Login again to reset.",
                    }
                )
            except Exception as e:
                await self._send({"ok": False, "error": str(e)})
            return

        # ── Tool command ──────────────────────────────────────────────────────

        if cmd == "tool":
            tool_name = request.get("tool", "")
            method_name = request.get("method", "")
            tool_args = request.get("args", {})

            # Check permissions if session is logged in
            if self._session:
                permissions = self._session.permissions
                if not permissions.can_use(tool_name):
                    await self._send(
                        {
                            "ok": False,
                            "error": f"Permission denied for tool: {tool_name}",
                        }
                    )
                    return

            result = await self._execute_tool(tool_name, method_name, tool_args)
            if result.get("ok") is True:
                await self._send({"ok": True, "result": result.get("result")})
            else:
                await self._send(
                    {"ok": False, "error": result.get("error", "unknown error")}
                )
            return

        await self._send({"ok": False, "error": f"Unknown cmd: {cmd}"})

    # ── Tool execution ─────────────────────────────────────────────────────────

    async def _execute_tool(
        self, tool_name: str, method_name: str, tool_args: dict
    ) -> dict:
        """Instantiate a registered service tool class and call the named method."""
        if tool_name not in self.kernel.tools:
            return {"ok": False, "error": f"Tool not found: {tool_name}"}

        try:
            tool_class = self.kernel.tools[tool_name]
            if not method_name:
                return {
                    "ok": False,
                    "error": f"No method specified for tool '{tool_name}'",
                }
            if not hasattr(tool_class, method_name):
                return {
                    "ok": False,
                    "error": f"Method '{method_name}' not found on {tool_name}",
                }

            instance = tool_class()
            method = getattr(instance, method_name)
            result = method(**tool_args)

            import inspect

            if inspect.iscoroutine(result):
                result = await result
            if isinstance(result, (dict, list)):
                result = json.dumps(result)
            return {"ok": True, "result": result}
        except TypeError as e:
            return {
                "ok": False,
                "error": f"Bad args for {tool_name}.{method_name}: {e}",
            }
        except Exception as e:
            return {"ok": False, "error": f"{tool_name}.{method_name} failed: {e}"}

    # ── Response writer ───────────────────────────────────────────────────────

    async def _send(self, payload: dict) -> None:
        """Serialize dict to JSON line and write to transport."""
        if self.transport is None:
            return
        data = json.dumps(payload).encode("utf-8") + b"\n"
        self.transport.write(data)


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------


class SocketServer:
    """
    Manages both Unix-domain and TCP socket servers for the shell bridge.

    Holds a shared SessionManager so all connections share the same session
    state across the machine.
    """

    def __init__(
        self,
        unix_path: str | None = None,
        tcp_host: str = "127.0.0.1",
        tcp_port: int | None = None,
    ) -> None:
        self.unix_path = unix_path or os.environ.get(
            "BANTU_SOCK_PATH", "/tmp/bantu.sock"
        )
        self.tcp_host = tcp_host
        self.tcp_port = int(os.environ.get("BANTU_TCP_PORT", str(tcp_port or 18792)))
        self._session_manager: Optional[SessionManager] = None
        self._kernel: Optional[Kernel] = None
        self._unix_server: Optional[asyncio.Server] = None
        self._tcp_server: Optional[asyncio.Server] = None
        self._shutdown_event = asyncio.Event()
        self._started_event = asyncio.Event()

    @property
    def session_manager(self) -> SessionManager:
        if self._session_manager is None:
            self._session_manager = SessionManager()
        return self._session_manager

    async def _make_protocol_factory(self):
        """Return a factory that creates ShellProtocol with shared session manager."""
        loop = asyncio.get_running_loop()

        def factory() -> ShellProtocol:
            return ShellProtocol(self.session_manager, loop)

        return factory

    async def _run_unix_server(self) -> None:
        """Start Unix-domain socket server on self.unix_path."""
        if os.path.exists(self.unix_path):
            os.unlink(self.unix_path)

        loop = asyncio.get_running_loop()
        factory = await self._make_protocol_factory()

        self._unix_server = await loop.create_unix_server(
            factory,
            path=self.unix_path,
        )
        os.chmod(self.unix_path, 0o666)
        print(f"Unix socket listening on {self.unix_path}", flush=True)

    async def _run_tcp_server(self) -> None:
        """Start TCP socket server on self.tcp_host:self.tcp_port."""
        loop = asyncio.get_running_loop()
        factory = await self._make_protocol_factory()

        self._tcp_server = await loop.create_server(
            factory,
            host=self.tcp_host,
            port=self.tcp_port,
        )
        for sock in self._tcp_server.sockets or []:
            if sock.family == socket.AF_INET:
                actual = sock.getsockname()
                print(f"TCP socket listening on {actual[0]}:{actual[1]}", flush=True)
                break

    async def run(self) -> None:
        """Start both servers and run until shutdown is signalled."""
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig, lambda s=sig: asyncio.create_task(self.shutdown(s))
            )

        await self._run_unix_server()
        await self._run_tcp_server()

        print("Shell bridge ready.", flush=True)
        self._started_event.set()

        await self._shutdown_event.wait()

    async def shutdown(self, sig: Optional[signal.Signals] = None) -> None:
        """Graceful shutdown: stop servers, unlink socket, set event."""
        if sig is not None:
            name = sig.name if hasattr(sig, "name") else str(sig)
            print(f"\nShutdown requested ({name})…", flush=True)
        else:
            print("\nShutting down…", flush=True)

        self._shutdown_event.set()

        if self._unix_server:
            self._unix_server.close()
            await self._unix_server.wait_closed()
            self._unix_server = None
        if self._tcp_server:
            self._tcp_server.close()
            await self._tcp_server.wait_closed()
            self._tcp_server = None

        if os.path.exists(self.unix_path):
            try:
                os.unlink(self.unix_path)
            except FileNotFoundError:
                pass

        print("Shell bridge stopped.", flush=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    server = SocketServer()
    try:
        await server.run()
    except KeyboardInterrupt:
        await server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
