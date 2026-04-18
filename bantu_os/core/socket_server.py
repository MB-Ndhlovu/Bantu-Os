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
from pathlib import Path
from typing import Any, Optional

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from bantu_os.core.kernel import Kernel
from bantu_os.services.file_service import FileService
from bantu_os.services.process_service import ProcessService
from bantu_os.services.network_service import NetworkService

# Phase 2: Messaging, Fintech, Crypto
try:
    from bantu_os.services.messaging import MessagingService
    from bantu_os.services.fintech import FintechService
    from bantu_os.services.crypto import CryptoWalletService
    _PHASE2_AVAILABLE = True
except ImportError:
    _PHASE2_AVAILABLE = False

# Phase 3: IoT, Hardware
try:
    from bantu_os.services.iot import IoTService
    from bantu_os.services.hardware import HardwareService
    _IOT_AVAILABLE = True
    _HARDWARE_AVAILABLE = True
except ImportError:
    _IOT_AVAILABLE = False
    _HARDWARE_AVAILABLE = False


def make_kernel() -> Kernel:
    """
    Build a Kernel with all services registered as tools.

    Services are registered as CLASSES (not instances) so each tool call
    instantiates a fresh service object with the caller's kwargs.
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

    print(f"[kernel] Phase 2 services registered: messaging, fintech, crypto" if _PHASE2_AVAILABLE else "[kernel] Phase 2: not available")
    if _IOT_AVAILABLE or _HARDWARE_AVAILABLE:
        registered = [_f for _f in [("iot" if _IOT_AVAILABLE else None), ("hardware" if _HARDWARE_AVAILABLE else None)] if _f]
        print(f"[kernel] Phase 3 services registered: {', '.join(registered)}")

    return kernel


# ---------------------------------------------------------------------------
# Per-client protocol handler
# ---------------------------------------------------------------------------

class ShellProtocol(asyncio.Protocol):
    """
    asyncio Protocol for a line-buffered JSON socket session.

    State machine per connection:
      buffer -> accumulate bytes until '\\n' -> decode JSON line -> process -> respond
    """

    __slots__ = ("kernel", "loop", "transport", "buffer")

    def __init__(self, kernel: Kernel, loop: asyncio.AbstractEventLoop) -> None:
        self.kernel = kernel
        self.loop = loop
        self.transport: Optional[asyncio.Transport] = None
        self.buffer: bytearray = bytearray()

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

        if cmd == "ai":
            text = request.get("text", "")
            try:
                result = await self.kernel.process_input(text)
                await self._send({"ok": True, "result": result})
            except Exception as e:
                await self._send({"ok": False, "error": str(e)})
            return

        if cmd == "tool":
            tool_name = request.get("tool", "")
            method_name = request.get("method", "")
            tool_args = request.get("args", {})
            result = await self._execute_tool(tool_name, method_name, tool_args)
            if result.get("ok") is True:
                await self._send({"ok": True, "result": result.get("result")})
            else:
                await self._send({"ok": False, "error": result.get("error", "unknown error")})
            return

        await self._send({"ok": False, "error": f"Unknown cmd: {cmd}"})

    async def _execute_tool(
        self, tool_name: str, method_name: str, tool_args: dict
    ) -> dict:
        """
        Instantiate a registered service tool class and call the named method.

        Protocol:
            tool_name   — registered tool name (e.g. "file", "process", "network")
            method_name — method on the service instance (e.g. "read", "get_system_stats")
            tool_args   — passed to the METHOD, not the constructor
        """
        if tool_name not in self.kernel.tools:
            return {"ok": False, "error": f"Tool not found: {tool_name}"}

        try:
            tool_class = self.kernel.tools[tool_name]
            if not method_name:
                return {"ok": False, "error": f"No method specified for tool '{tool_name}'"}
            if not hasattr(tool_class, method_name):
                return {"ok": False, "error": f"Method '{method_name}' not found on {tool_name}"}
            # Instantiate with no constructor args (services are stateless/config-free)
            instance = tool_class()
            method = getattr(instance, method_name)
            result = method(**tool_args)
            # Async tool methods (async def) return coroutines — await them
            import inspect
            if inspect.iscoroutine(result):
                result = await result
            # Serialize dict/list results as JSON strings for the shell consumer
            if isinstance(result, (dict, list)):
                result = json.dumps(result)
            return {"ok": True, "result": result}
        except TypeError as e:
            return {"ok": False, "error": f"Bad args for {tool_name}.{method_name}: {e}"}
        except Exception as e:
            return {"ok": False, "error": f"{tool_name}.{method_name} failed: {e}"}

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

    Args:
        unix_path:  path for the Unix domain socket (default /tmp/bantu.sock)
                    Override with BANTU_SOCK_PATH env var.
        tcp_host:   host to bind TCP server on (default 127.0.0.1)
        tcp_port:   port for TCP server (default 18792, 0xBANTU in hex)
                    Override with BANTU_TCP_PORT env var.
    """

    def __init__(
        self,
        unix_path: str | None = None,
        tcp_host: str = "127.0.0.1",
        tcp_port: int | None = None,
    ) -> None:
        self.unix_path = unix_path or os.environ.get("BANTU_SOCK_PATH", "/tmp/bantu.sock")
        self.tcp_host = tcp_host
        self.tcp_port = int(os.environ.get("BANTU_TCP_PORT", str(tcp_port or 18792)))
        self._kernel: Optional[Kernel] = None
        self._unix_server: Optional[asyncio.Server] = None
        self._tcp_server: Optional[asyncio.Server] = None
        self._shutdown_event = asyncio.Event()
        self._started_event = asyncio.Event()

    async def _get_kernel(self) -> Kernel:
        if self._kernel is None:
            self._kernel = make_kernel()
        return self._kernel

    # ------------------------------------------------------------------
    # Unix socket
    # ------------------------------------------------------------------

    async def _run_unix_server(self) -> None:
        """Start Unix-domain socket server on self.unix_path."""
        if os.path.exists(self.unix_path):
            os.unlink(self.unix_path)

        kernel = await self._get_kernel()
        loop = asyncio.get_running_loop()

        self._unix_server = await loop.create_unix_server(
            lambda: ShellProtocol(kernel, loop),
            path=self.unix_path,
        )
        os.chmod(self.unix_path, 0o666)
        print(f"Unix socket listening on {self.unix_path}", flush=True)

    # ------------------------------------------------------------------
    # TCP socket (optional multi-client / future telnet bridge)
    # ------------------------------------------------------------------

    async def _run_tcp_server(self) -> None:
        """Start TCP socket server on self.tcp_host:self.tcp_port."""
        kernel = await self._get_kernel()
        loop = asyncio.get_running_loop()

        self._tcp_server = await loop.create_server(
            lambda: ShellProtocol(kernel, loop),
            host=self.tcp_host,
            port=self.tcp_port,
        )
        # Find the actual port bound (in case port=0 was used)
        for sock in self._tcp_server.sockets or []:
            if sock.family == socket.AF_INET:
                actual = sock.getsockname()
                print(f"TCP socket listening on {actual[0]}:{actual[1]}", flush=True)
                break

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """
        Start both servers and run until shutdown is signalled.

        Signal handlers for SIGINT and SIGTERM trigger graceful shutdown.
        """
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(self.shutdown(s)))

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
