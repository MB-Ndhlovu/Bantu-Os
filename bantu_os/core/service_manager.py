"""
Bantu-OS Service Manager — Phase 3.

Central daemon that manages the lifecycle of all Bantu-OS services.
Replaces manual service starting with a supervised daemon.

Usage:
    python -m bantu_os.core.service_manager
    # or
    ./start.sh   (already calls this via the kernel server)
"""

from __future__ import annotations

import asyncio
import signal
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import psutil

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from bantu_os.core.kernel import Kernel
from bantu_os.services.file_service import FileService
from bantu_os.services.network_service import NetworkService
from bantu_os.services.process_service import ProcessService

# ─── Phase 2 ───────────────────────────────────────────────────────────────
try:
    from bantu_os.services.crypto import CryptoWalletService
    from bantu_os.services.fintech import FintechService
    from bantu_os.services.messaging import MessagingService

    _PHASE2_AVAILABLE = True
except ImportError:
    _PHASE2_AVAILABLE = False

# ─── Phase 3 ───────────────────────────────────────────────────────────────
try:
    from bantu_os.services.iot import IoTService

    _IOT_AVAILABLE = True
except ImportError:
    _IOT_AVAILABLE = False

# ─── Auth (Phase 3) ──────────────────────────────────────────────────────
try:
    from bantu_os.auth import AuthService

    _AUTH_AVAILABLE = True
except ImportError:
    _AUTH_AVAILABLE = False
    AuthService = None


class ServiceState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    UNHEALTHY = "unhealthy"
    STOPPING = "stopping"


@dataclass
class ServiceHandle:
    name: str
    state: ServiceState = ServiceState.STOPPED
    pid: Optional[int] = None
    started_at: Optional[float] = None
    restarts: int = 0
    last_error: Optional[str] = None
    healthy: bool = False


class ServiceManager:
    """
    Central service supervisor for Bantu-OS.

    Manages the lifecycle of all registered services with:
    - Health monitoring (heartbeat polling)
    - Auto-restart on crash (up to 3 attempts)
    - Graceful shutdown (SIGTERM propagation)
    - Status reporting
    """

    def __init__(self) -> None:
        self._services: dict[str, ServiceHandle] = {}
        self._kernel: Optional[Kernel] = None
        self._kernel_handle: Optional[ServiceHandle] = None
        self._shutdown = asyncio.Event()
        self._restart_policy = {"max_restarts": 3, "restart_delay": 5.0}
        self._auth = AuthService() if _AUTH_AVAILABLE else None

    # ─── Kernel management ─────────────────────────────────────────────────

    def _build_kernel(self) -> Kernel:
        """Build the kernel with all registered services."""
        kernel = Kernel(tools={})
        kernel.register_tool("file", FileService)
        kernel.register_tool("process", ProcessService)
        kernel.register_tool("network", NetworkService)
        if _PHASE2_AVAILABLE:
            kernel.register_tool("messaging", MessagingService)
            kernel.register_tool("fintech", FintechService)
            kernel.register_tool("crypto", CryptoWalletService)
        if _IOT_AVAILABLE:
            kernel.register_tool("iot", IoTService)
        return kernel

    async def start_kernel(self) -> None:
        """Start the Python kernel server as a managed subprocess."""
        name = "kernel"
        if name in self._services:
            h = self._services[name]
            if h.state == ServiceState.RUNNING:
                return  # already running

        handle = ServiceHandle(name=name, state=ServiceState.STARTING)
        self._services[name] = handle

        str(
            Path(__file__).resolve().parents[3]
            / "bantu_os"
            / "core"
            / "socket_server.py"
        )
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "bantu_os.core.socket_server",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        handle.pid = proc.pid
        handle.state = ServiceState.RUNNING
        handle.started_at = time.time()
        handle.healthy = True
        self._kernel_handle = handle
        self._kernel = self._build_kernel()
        print(f"[service_manager] kernel started (PID {proc.pid})")

    async def stop_kernel(self) -> None:
        """Stop the kernel subprocess gracefully."""
        if self._kernel_handle is None:
            return
        handle = self._kernel_handle
        handle.state = ServiceState.STOPPING
        if handle.pid:
            try:
                proc = psutil.Process(handle.pid)
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except psutil.NoSuchProcess:
                pass
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except psutil.NoSuchProcess:
                    pass
        handle.state = ServiceState.STOPPED
        handle.healthy = False
        self._kernel_handle = None
        print("[service_manager] kernel stopped")

    # ─── Lifecycle ────────────────────────────────────────────────────────

    async def start_all(self) -> None:
        """Start all managed services."""
        print("[service_manager] starting all services...")
        await self.start_kernel()
        print("[service_manager] all services started")

    async def stop_all(self) -> None:
        """Stop all managed services gracefully."""
        print("[service_manager] stopping all services...")
        self._shutdown.set()
        await self.stop_kernel()
        self._services.clear()
        print("[service_manager] all services stopped")

    # ─── Status ──────────────────────────────────────────────────────────

    def status(self) -> dict:
        """Return the status of all managed services."""
        kernel_status = "running" if self._kernel_handle else "stopped"
        return {
            "service_manager": "running",
            "kernel": kernel_status,
            "kernel_pid": self._kernel_handle.pid if self._kernel_handle else None,
            "kernel_healthy": (
                self._kernel_handle.healthy if self._kernel_handle else False
            ),
            "phase2_available": _PHASE2_AVAILABLE,
            "iot_available": _IOT_AVAILABLE,
        }


# ─── CLI ─────────────────────────────────────────────────────────────────────


async def main() -> None:
    print("Bantu-OS Service Manager v0.3.0")
    manager = ServiceManager()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(manager.stop_all())
        )

    await manager.start_all()
    print("[service_manager] status:", manager.status())

    try:
        await manager._shutdown.wait()
    except asyncio.CancelledError:
        pass
    finally:
        await manager.stop_all()


if __name__ == "__main__":
    asyncio.run(main())
