"""Process supervisor for Bantu-OS service management.

Provides a Supervisor class that can start, stop, restart, and monitor
child processes with automatic restart on crash.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Paths
RUN_DIR = Path("/var/run/bantu")
LOG_DIR = Path("/var/log/bantu")
SOCKET_PATH = Path("/tmp/bantu.sock")

SERVICE_KERNEL = "kernel"
SERVICE_SHELL = "shell"
ALL_SERVICES = [SERVICE_KERNEL, SERVICE_SHELL]


@dataclass
class ServiceDefinition:
    """Definition of a managed service."""

    name: str
    command: list[str]
    env: dict[str, str]
    pid_file: Path
    log_file: Path
    socket_path: Optional[Path] = None
    restart_delay: float = 3.0
    max_restarts: int = 5
    restart_window: float = 60.0  # seconds

    # Runtime state
    pid: Optional[int] = None
    restarts: int = 0
    first_start_time: float = field(default_factory=time.time)
    last_crash_time: float = 0.0
    proc: Optional[asyncio.subprocess.Process] = None


class Supervisor:
    """Manages Bantu-OS services as supervised child processes."""

    def __init__(self) -> None:
        self.services: dict[str, ServiceDefinition] = {}
        self._shutdown_requested = False
        self._monitor_task: Optional[asyncio.Task[None]] = None

    def register_services(self, project_root: Path) -> None:
        """Register all Bantu-OS services."""
        kernel_env = dict(os.environ)
        kernel_env["PYTHONPATH"] = str(project_root)
        kernel_log = LOG_DIR / "kernel.log"

        self.services[SERVICE_KERNEL] = ServiceDefinition(
            name=SERVICE_KERNEL,
            command=[
                sys.executable,
                "-m",
                "bantu_os.core.socket_server",
            ],
            env=kernel_env,
            pid_file=RUN_DIR / "kernel.pid",
            log_file=kernel_log,
            socket_path=SOCKET_PATH,
        )

        shell_bin = project_root / "shell" / "target" / "release" / "bantu"
        self.services[SERVICE_SHELL] = ServiceDefinition(
            name=SERVICE_SHELL,
            command=[str(shell_bin)],
            env={},
            pid_file=RUN_DIR / "shell.pid",
            log_file=LOG_DIR / "shell.log",
        )

    def _ensure_dirs(self) -> None:
        """Create run and log directories."""
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    # ── Process control ──────────────────────────────────────────────────────

    async def start_service(self, name: str) -> bool:
        """Start a service. Returns True if started successfully."""
        if name not in self.services:
            raise ValueError(f"Unknown service: {name}")

        svc = self.services[name]

        if svc.pid is not None and await self._is_running(svc.pid):
            logger.info("[supervisor] %s already running (PID %s)", name, svc.pid)
            return True

        self._ensure_dirs()

        # Open log file
        log_fp = open(svc.log_file, "ab")

        logger.info("[supervisor] Starting %s: %s", name, " ".join(svc.command))
        try:
            proc = await asyncio.create_subprocess_exec(
                *svc.command,
                env={**os.environ, **svc.env},
                stdout=log_fp,
                stderr=subprocess.STDOUT,
            )
        except FileNotFoundError:
            logger.error("[supervisor] Command not found: %s", svc.command[0])
            return False

        svc.pid = proc.pid
        svc.proc = proc
        svc.pid_file.write_text(str(proc.pid))
        logger.info("[supervisor] %s started (PID %s)", name, proc.pid)
        return True

    async def stop_service(self, name: str, timeout: float = 10.0) -> bool:
        """Stop a service gracefully. Returns True if stopped."""
        if name not in self.services:
            raise ValueError(f"Unknown service: {name}")

        svc = self.services[name]

        if svc.pid is None or not await self._is_running(svc.pid):
            logger.info("[supervisor] %s not running", name)
            svc.pid = None
            if svc.pid_file.exists():
                svc.pid_file.unlink()
            return True

        logger.info("[supervisor] Stopping %s (PID %s)", name, svc.pid)
        try:
            os.kill(svc.pid, signal.SIGTERM)
        except ProcessLookupError:
            logger.info("[supervisor] %s already dead", name)
            svc.pid = None
            return True

        # Wait for graceful shutdown
        try:
            await asyncio.wait_for(self._wait_pid(svc.pid), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("[supervisor] %s did not exit gracefully, killing", name)
            try:
                os.kill(svc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        svc.pid = None
        svc.proc = None
        if svc.pid_file.exists():
            svc.pid_file.unlink()
        logger.info("[supervisor] %s stopped", name)
        return True

    async def restart_service(self, name: str) -> bool:
        """Restart a service."""
        await self.stop_service(name)
        return await self.start_service(name)

    async def start_all(self) -> None:
        """Start all registered services."""
        for name in ALL_SERVICES:
            if name in self.services:
                await self.start_service(name)

    async def stop_all(self) -> None:
        """Stop all services gracefully."""
        for name in reversed(ALL_SERVICES):
            if name in self.services:
                await self.stop_service(name)

    # ── Monitoring ────────────────────────────────────────────────────────────

    async def _is_running(self, pid: int) -> bool:
        """Check if a PID is running."""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    async def _wait_pid(self, pid: int) -> None:
        """Wait for a process to exit."""
# loop acquired implicitly by asyncio.wait_for
        while True:
            try:
                os.kill(pid, 0)
            except OSError:
                return
            await asyncio.sleep(0.5)

    async def _monitor_loop(self) -> None:
        """Monitor all services, restarting crashed ones."""
        restart_count: dict[str, int] = {name: 0 for name in self.services}

        while not self._shutdown_requested:
            await asyncio.sleep(5)

            for name, svc in self.services.items():
                if svc.pid is None:
                    continue

                proc = svc.proc
                if (
                    proc is not None
                    and proc.returncode is not None
                    and proc.returncode != 0
                ):
                    # Crashed
                    now = time.time()
                    svc.last_crash_time = now

                    if now - svc.first_start_time > svc.restart_window:
                        restart_count[name] = 0
                        svc.first_start_time = now

                    restart_count[name] += 1
                    logger.warning(
                        "[supervisor] %s crashed (exit %s), restart %s/%s",
                        name,
                        proc.returncode,
                        restart_count[name],
                        svc.max_restarts,
                    )

                    svc.pid = None
                    svc.proc = None
                    if svc.pid_file.exists():
                        svc.pid_file.unlink()

                    if restart_count[name] <= svc.max_restarts:
                        await asyncio.sleep(svc.restart_delay)
                        await self.start_service(name)
                    else:
                        logger.error(
                            "[supervisor] %s exceeded max restarts (%s), giving up",
                            name,
                            svc.max_restarts,
                        )
                        restart_count[name] = 0

    async def run(self) -> None:
        """Start the supervisor: create dirs, start all services, monitor."""
        self._ensure_dirs()
        await self.start_all()
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            pass
        finally:
            self._shutdown_requested = True
            if self._monitor_task:
                self._monitor_task.cancel()
            await self.stop_all()

    # ── Status ───────────────────────────────────────────────────────────────

    def status(self) -> dict[str, dict]:
        """Return status of all services."""
        result = {}
        for name, svc in self.services.items():
            running = svc.pid is not None
            if svc.pid is not None:
                try:
                    os.kill(svc.pid, 0)
                except OSError:
                    running = False

            result[name] = {
                "running": running,
                "pid": svc.pid,
                "log": str(svc.log_file),
                "socket": str(svc.socket_path) if svc.socket_path else None,
            }
        return result
