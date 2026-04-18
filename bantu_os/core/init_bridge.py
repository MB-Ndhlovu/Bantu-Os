"""
Bantu-OS Init Bridge — Python service registration with C init.

This module connects the Python AI engine to the C init system's
service registry via a Unix domain socket at /run/bantu/init.sock.

C init acts as PID 1 in the Bantu-OS environment. Services register
their name and PID on startup, send heartbeats, and handle SIGTERM
gracefully on shutdown.
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

SOCKET_PATH = "/run/bantu/init.sock"


class InitBridge:
    """
    Client for the C init service registry socket protocol.

    The C init exposes a Unix domain socket at /run/bantu/init.sock
    for services to:
      - Register (send their name + PID)
      - Report health (heartbeat)
      - Receive shutdown signals (SIGTERM propagated from init)
    """

    def __init__(self, service_name: str = "ai-engine", socket_path: str = SOCKET_PATH):
        self.service_name = service_name
        self.socket_path = socket_path
        self.sock: Optional[socket.socket] = None
        self._shutdown_event = asyncio.Event()
        self._registered = False

    # -------------------------------------------------------------------------
    # Socket communication
    # -------------------------------------------------------------------------

    def _connect(self) -> None:
        """Establish connection to the C init socket."""
        # Ensure directory exists
        socket_dir = Path(self.socket_path).parent
        socket_dir.mkdir(parents=True, exist_ok=True)

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)

    def _send(self, payload: dict) -> dict:
        """Send a JSON message and receive the response."""
        if self.sock is None:
            raise RuntimeError("Not connected to init socket")
        data = json.dumps(payload).encode("utf-8") + b"\n"
        self.sock.sendall(data)
        response = self.sock.recv(4096).decode("utf-8", errors="replace")
        return json.loads(response.strip())

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def register(self) -> bool:
        """
        Register this service with the C init registry.

        Sends: {"cmd": "register", "name": "<service_name>", "pid": <pid>}
        Expected: {"ok": true, "message": "registered"} or similar

        Returns True on success, False on failure.
        """
        try:
            self._connect()
            resp = self._send({
                "cmd": "register",
                "name": self.service_name,
                "pid": os.getpid(),
            })
            self._registered = True
            return resp.get("ok", False)
        except (ConnectionRefusedError, FileNotFoundError, json.JSONDecodeError):
            # C init socket not available — not running inside the init environment.
            # This is normal for development outside the init environment.
            return False
        except Exception:
            return False

    def unregister(self) -> None:
        """Unregister this service from the C init registry."""
        if not self._registered or self.sock is None:
            return
        try:
            self._send({"cmd": "unregister", "name": self.service_name})
        except Exception:
            pass
        finally:
            self.sock.close()
            self.sock = None
            self._registered = False

    # -------------------------------------------------------------------------
    # Heartbeat
    # -------------------------------------------------------------------------

    def heartbeat(self) -> bool:
        """
        Send a heartbeat to the C init to signal the service is healthy.

        Returns True if the init acknowledges, False otherwise.
        """
        if self.sock is None:
            return False
        try:
            resp = self._send({"cmd": "heartbeat", "name": self.service_name})
            return resp.get("ok", False)
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------

    def get_service_status(self, name: str) -> Optional[dict]:
        """Query the C init for another service's status."""
        if self.sock is None:
            return None
        try:
            resp = self._send({"cmd": "status", "name": name})
            return resp if resp.get("ok") else None
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # Shutdown signal handling
    # -------------------------------------------------------------------------

    def setup_sigterm_handler(self) -> None:
        """
        Register a SIGTERM handler that sets the shutdown event.

        When C init propagates SIGTERM to this service, the event is set
        allowing the service to perform graceful cleanup before exiting.
        """
        loop = asyncio.get_running_loop()
        def handler(sig: signal.Signals) -> None:
            print(f"[init-bridge] Received SIGTERM, initiating graceful shutdown…")
            self._shutdown_event.set()
        loop.add_signal_handler(signal.SIGTERM, handler)

    @property
    def shutdown_event(self) -> asyncio.Event:
        return self._shutdown_event

    # -------------------------------------------------------------------------
    # Context manager (clean connect/disconnect)
    # -------------------------------------------------------------------------

    async def __aenter__(self) -> "InitBridge":
        """Register with C init on startup."""
        loop = asyncio.get_running_loop()
        # Run registration in thread pool to avoid blocking the event loop
        registered = await loop.run_in_executor(None, self.register)
        if registered:
            print(f"[init-bridge] Registered with C init as '{self.service_name}'")
        else:
            print(f"[init-bridge] C init socket not found at {SOCKET_PATH} — running standalone")
        self.setup_sigterm_handler()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Unregister from C init on shutdown."""
        await asyncio.get_running_loop().run_in_executor(None, self.unregister)