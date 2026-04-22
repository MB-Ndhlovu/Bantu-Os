"""Service Manager daemon for Bantu-OS.

Listens on /tmp/bantu-admin.sock for CLI commands and manages the lifecycle
of Bantu-OS services (kernel + shell) via the Supervisor.

Commands over Unix socket:
  {"cmd": "status"}                        → {"ok": true, "result": {...}}
  {"cmd": "start", "service": "kernel"}    → {"ok": true, "result": "started"}
  {"cmd": "stop", "service": "kernel"}     → {"ok": true, "result": "stopped"}
  {"cmd": "restart", "service": "kernel"}  → {"ok": true, "result": "restarted"}
  {"cmd": "logs", "service": "kernel"}     → {"ok": true, "result": "<last 100 lines>"}
  {"cmd": "shutdown"}                      → {"ok": true}  (stops daemon)
  {"cmd": "ping"}                          → {"ok": true, "result": "pong"}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from pathlib import Path
from typing import Optional

from bantu_os.services.supervisor import (
    Supervisor,
)

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
logger = logging.getLogger("service_manager")

ADMIN_SOCK_PATH = "/tmp/bantu-admin.sock"
TAIL_LINES = 100


class AdminProtocol(asyncio.Protocol):
    """Handle JSON commands from bantu-admin CLI."""

    __slots__ = ("supervisor", "transport", "buffer")

    def __init__(self, supervisor: Supervisor) -> None:
        self.supervisor = supervisor
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

    async def _process(self, line: str) -> None:
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            await self._send({"ok": False, "error": f"Invalid JSON: {e}"})
            return

        cmd = req.get("cmd", "")
        service = req.get("service")

        try:
            if cmd == "ping":
                await self._send({"ok": True, "result": "pong"})

            elif cmd == "status":
                result = self.supervisor.status()
                await self._send({"ok": True, "result": result})

            elif cmd == "start":
                if not service:
                    await self._send({"ok": False, "error": "service name required"})
                    return
                ok = await self.supervisor.start_service(service)
                await self._send({"ok": ok, "result": f"{service} started"})

            elif cmd == "stop":
                if not service:
                    await self._send({"ok": False, "error": "service name required"})
                    return
                ok = await self.supervisor.stop_service(service)
                await self._send({"ok": ok, "result": f"{service} stopped"})

            elif cmd == "restart":
                if not service:
                    await self._send({"ok": False, "error": "service name required"})
                    return
                ok = await self.supervisor.restart_service(service)
                await self._send({"ok": ok, "result": f"{service} restarted"})

            elif cmd == "logs":
                if not service:
                    await self._send({"ok": False, "error": "service name required"})
                    return
                if service not in self.supervisor.services:
                    await self._send(
                        {"ok": False, "error": f"unknown service: {service}"}
                    )
                    return
                log_path = self.supervisor.services[service].log_file
                try:
                    lines = log_path.read_text(encoding="utf-8").splitlines()
                    tail = "\n".join(lines[-TAIL_LINES:])
                    await self._send({"ok": True, "result": tail})
                except FileNotFoundError:
                    await self._send(
                        {"ok": False, "error": f"log not found: {log_path}"}
                    )
                except Exception as e:
                    await self._send({"ok": False, "error": str(e)})

            elif cmd == "shutdown":
                await self._send({"ok": True, "result": "shutting down"})
                self.supervisor._shutdown_requested = True

            else:
                await self._send({"ok": False, "error": f"Unknown cmd: {cmd}"})

        except Exception as e:
            await self._send({"ok": False, "error": str(e)})

    async def _send(self, payload: dict) -> None:
        if self.transport is None:
            return
        data = json.dumps(payload).encode("utf-8") + b"\n"
        self.transport.write(data)


async def run_daemon(project_root: Path) -> None:
    """Start the service manager daemon."""
    if os.path.exists(ADMIN_SOCK_PATH):
        os.unlink(ADMIN_SOCK_PATH)

    supervisor = Supervisor()
    supervisor.register_services(project_root)

    loop = asyncio.get_running_loop()

    def shutdown_signal(sig: signal.Signals) -> None:
        logger.info("Received %s, shutting down...", sig.name)
        supervisor._shutdown_requested = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_signal, sig)

    server = await loop.create_unix_server(
        lambda: AdminProtocol(supervisor),
        path=ADMIN_SOCK_PATH,
    )
    os.chmod(ADMIN_SOCK_PATH, 0o666)
    logger.info("Service manager listening on %s", ADMIN_SOCK_PATH)

    try:
        await supervisor.run()
    finally:
        server.close()
        await server.wait_closed()
        if os.path.exists(ADMIN_SOCK_PATH):
            os.unlink(ADMIN_SOCK_PATH)


def main() -> None:
    project_root = Path(__file__).resolve().parents[3]
    asyncio.run(run_daemon(project_root))


if __name__ == "__main__":
    main()
