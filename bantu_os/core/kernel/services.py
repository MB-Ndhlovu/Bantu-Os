"""
ServiceManager — Bantu-OS service orchestrator.

Manages the lifecycle of all Bantu-OS services: discovers them,
starts/stops them, runs health checks, and optionally restarts crashed
services.

Usage:
    from bantu_os.core.kernel.services import ServiceManager

    mgr = ServiceManager()
    await mgr.discover_services()
    await mgr.start_all()
    status = await mgr.health_check_all()
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)


class ServiceStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPING = "stopping"


@dataclass
class ServiceDescriptor:
    """Metadata about a registered service."""
    name: str
    description: str
    version: str = "0.1.0"


@dataclass
class ManagedService:
    """Runtime state of a managed service."""
    descriptor: ServiceDescriptor
    instance: Any = field(default=None)
    status: ServiceStatus = ServiceStatus.STOPPED
    health_check_fn: Optional[Callable[[], Any]] = field(default=None)
    restart_policy: str = "none"          # "none" | "on-failure" | "always"
    restart_count: int = 0
    max_restarts: int = 3
    last_health_check: Optional[datetime] = None
    last_error: Optional[str] = None
    started_at: Optional[datetime] = None


class ServiceManager:
    """
    Central orchestrator for all Bantu-OS services.

    Responsibilities:
    - Discover available services (Phase 1–3 services)
    - Start/stop individual services or all at once
    - Periodic health checks with configurable intervals
    - Auto-restart on failure (per-service restart policy)
    - Event bus for service lifecycle events
    """

    def __init__(
        self,
        health_check_interval: float = 30.0,
        startup_timeout: float = 10.0,
    ) -> None:
        self._services: dict[str, ManagedService] = {}
        self._health_check_interval = health_check_interval
        self._startup_timeout = startup_timeout
        self._health_task: Optional[asyncio.Task] = None
        self._running = False

        # Optional event hooks
        self._on_service_started: list[Callable[[str], None]] = []
        self._on_service_stopped: list[Callable[[str], None]] = []
        self._on_service_failed: list[Callable[[str, str], None]] = []

    # ─── Discovery ──────────────────────────────────────────────────────────

    def register(
        self,
        name: str,
        instance: Any,
        description: str = "",
        version: str = "0.1.0",
        health_check_fn: Optional[Callable[[], Any]] = None,
        restart_policy: str = "none",
        max_restarts: int = 3,
    ) -> None:
        """Register a service instance with the manager."""
        if hasattr(instance, "health_check") and health_check_fn is None:
            health_check_fn = instance.health_check

        desc = ServiceDescriptor(
            name=name,
            description=description or getattr(instance, "__doc__", ""),
            version=version,
        )
        self._services[name] = ManagedService(
            descriptor=desc,
            instance=instance,
            health_check_fn=health_check_fn,
            restart_policy=restart_policy,
            max_restarts=max_restarts,
        )
        log.info("[svc] registered: %s (%s)", name, version)

    def discover_services(self) -> None:
        """
        Auto-discover all Phase 1–3 services and register them.

        Loads service classes from the known service modules and registers
        each with sensible defaults.
        """
        discovered = []

        # Phase 1 services
        for svc_info in [
            ("file",    "bantu_os.services.file_service",    "FileService",    "file read/write/search", "on-failure"),
            ("process", "bantu_os.services.process_service",   "ProcessService",  "process spawn/kill/stats", "on-failure"),
            ("network", "bantu_os.services.network_service",  "NetworkService",  "HTTP client, connectivity", "on-failure"),
        ]:
            name, module, cls_name, desc, policy = svc_info
            if self._try_register(name, module, cls_name, desc, policy):
                discovered.append(name)

        # Phase 2 services
        for svc_info in [
            ("messaging", "bantu_os.services.messaging",      "MessagingService",    "email/SMS/Telegram", "on-failure"),
            ("fintech",   "bantu_os.services.fintech",        "FintechService",      "Stripe/M-Pesa/Flutterwave/Paystack", "on-failure"),
            ("crypto",    "bantu_os.services.crypto",           "CryptoWalletService", "EVM wallet: balance/send/sign", "on-failure"),
        ]:
            name, module, cls_name, desc, policy = svc_info
            if self._try_register(name, module, cls_name, desc, policy):
                discovered.append(name)

        # Phase 3 services
        for svc_info in [
            ("iot",       "bantu_os.services.iot",              "IoTService",         "MQTT broker, device registry, sensor ingestion", "on-failure"),
            ("hardware",  "bantu_os.services.hardware",         "HardwareService",    "CPU/memory/disk/GPIO/USB monitoring", "on-failure"),
        ]:
            name, module, cls_name, desc, policy = svc_info
            if self._try_register(name, module, cls_name, desc, policy):
                discovered.append(name)

        log.info("[svc] discovered %d services: %s", len(discovered), discovered)

    def _try_register(
        self,
        name: str,
        module: str,
        cls_name: str,
        description: str,
        restart_policy: str,
    ) -> bool:
        """Attempt to import and register a service. Returns True on success."""
        try:
            mod = __import__(module, fromlist=[cls_name])
            cls = getattr(mod, cls_name)
            self.register(name, cls(), description=description, restart_policy=restart_policy)
            return True
        except ImportError as e:
            log.debug("[svc] skip %s (%s not available): %s", name, module, e)
        except Exception as e:
            log.warning("[svc] failed to register %s: %s", name, e)
        return False

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def start_service(self, name: str) -> bool:
        """Start a single registered service."""
        svc = self._services.get(name)
        if svc is None:
            log.warning("[svc] unknown service: %s", name)
            return False
        if svc.status == ServiceStatus.HEALTHY:
            return True

        svc.status = ServiceStatus.STARTING
        try:
            if hasattr(svc.instance, "start"):
                start_fn = svc.instance.start
                if asyncio.iscoroutinefunction(start_fn):
                    await asyncio.wait_for(start_fn(), timeout=self._startup_timeout)
                else:
                    start_fn()
            svc.status = ServiceStatus.HEALTHY
            svc.started_at = datetime.utcnow()
            svc.last_error = None
            log.info("[svc] started: %s", name)
            self._fire("started", name)
            return True
        except Exception as e:
            svc.status = ServiceStatus.FAILED
            svc.last_error = str(e)
            log.error("[svc] failed to start %s: %s", name, e)
            self._fire("failed", name, str(e))
            return False

    async def stop_service(self, name: str) -> bool:
        """Stop a running service."""
        svc = self._services.get(name)
        if svc is None or svc.status == ServiceStatus.STOPPED:
            return True

        svc.status = ServiceStatus.STOPPING
        try:
            if hasattr(svc.instance, "stop"):
                stop_fn = svc.instance.stop
                if asyncio.iscoroutinefunction(stop_fn):
                    await stop_fn()
                else:
                    stop_fn()
            svc.status = ServiceStatus.STOPPED
            svc.instance = None
            log.info("[svc] stopped: %s", name)
            self._fire("stopped", name)
            return True
        except Exception as e:
            log.error("[svc] error stopping %s: %s", name, e)
            svc.status = ServiceStatus.FAILED
            return False

    async def start_all(self) -> dict[str, bool]:
        """Start all registered services. Returns map of name -> success."""
        results = {}
        for name in self._services:
            results[name] = await self.start_service(name)
        return results

    async def stop_all(self) -> None:
        """Stop all running services."""
        for name in list(self._services.keys()):
            await self.stop_service(name)

    # ─── Health checks ──────────────────────────────────────────────────────

    async def health_check_service(self, name: str) -> dict[str, Any]:
        """Run a health check on one service. Returns health report."""
        svc = self._services.get(name)
        if svc is None:
            return {"service": name, "status": "unknown", "error": "not found"}

        if svc.status not in (ServiceStatus.HEALTHY, ServiceStatus.DEGRADED):
            return {"service": name, "status": svc.status.value, "error": svc.last_error}

        if svc.health_check_fn is None:
            return {"service": name, "status": "healthy", "note": "no health check defined"}

        try:
            hc = svc.health_check_fn
            if asyncio.iscoroutinefunction(hc):
                result = await hc()
            else:
                result = hc()
            svc.last_health_check = datetime.utcnow()
            healthy = result.get("status") == "ok" if isinstance(result, dict) else result is True
            svc.status = ServiceStatus.HEALTHY if healthy else ServiceStatus.DEGRADED
            return {"service": name, "status": svc.status.value, "detail": result}
        except Exception as e:
            svc.status = ServiceStatus.DEGRADED
            svc.last_error = str(e)
            return {"service": name, "status": "degraded", "error": str(e)}

    async def health_check_all(self) -> dict[str, Any]:
        """Run health checks on all services."""
        results = {}
        for name in self._services:
            results[name] = await self.health_check_service(name)
        return results

    # ─── Background health monitor ─────────────────────────────────────────

    async def _run_health_monitor(self) -> None:
        """Background task: periodically checks service health and restarts failures."""
        while self._running:
            await asyncio.sleep(self._health_check_interval)
            if not self._running:
                break

            for name, svc in list(self._services.items()):
                report = await self.health_check_service(name)

                if svc.status == ServiceStatus.DEGRADED:
                    log.warning("[svc] %s is degraded: %s", name, report.get("error"))

                if svc.status == ServiceStatus.FAILED:
                    if svc.restart_policy in ("on-failure", "always"):
                        if svc.restart_count < svc.max_restarts:
                            svc.restart_count += 1
                            log.info("[svc] auto-restarting %s (attempt %d)", name, svc.restart_count)
                            await self.start_service(name)
                        else:
                            log.error("[svc] %s exceeded max restarts (%d)", name, svc.max_restarts)
                            self._fire("failed", name, "max restarts exceeded")

    def start_monitoring(self) -> None:
        """Start the background health monitor thread."""
        if self._health_task is not None:
            return
        self._running = True
        self._health_task = asyncio.create_task(self._run_health_monitor())
        log.info("[svc] health monitor started")

    def stop_monitoring(self) -> None:
        """Stop the background health monitor."""
        self._running = False
        if self._health_task is not None:
            self._health_task.cancel()
            self._health_task = None
            log.info("[svc] health monitor stopped")

    # ─── Event hooks ─────────────────────────────────────────────────────────

    def on_service_started(self, fn: Callable[[str], None]) -> None:
        self._on_service_started.append(fn)

    def on_service_stopped(self, fn: Callable[[str], None]) -> None:
        self._on_service_stopped.append(fn)

    def on_service_failed(self, fn: Callable[[str, str], None]) -> None:
        self._on_service_failed.append(fn)

    def _fire(self, event: str, *args: Any) -> None:
        if event == "started":
            for fn in self._on_service_started:
                fn(args[0])
        elif event == "stopped":
            for fn in self._on_service_stopped:
                fn(args[0])
        elif event == "failed":
            for fn in self._on_service_failed:
                fn(args[0], args[1])

    # ─── Introspection ──────────────────────────────────────────────────────

    @property
    def service_count(self) -> int:
        return len(self._services)

    @property
    def services(self) -> dict[str, ManagedService]:
        return self._services

    def list_services(self) -> list[dict[str, Any]]:
        """Return a summary of all registered services."""
        return [
            {
                "name": s.descriptor.name,
                "description": s.descriptor.description,
                "version": s.descriptor.version,
                "status": s.status.value,
                "restart_policy": s.restart_policy,
                "restart_count": s.restart_count,
                "last_error": s.last_error,
            }
            for s in self._services.values()
        ]
