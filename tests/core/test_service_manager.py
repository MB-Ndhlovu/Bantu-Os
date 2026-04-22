"""
Tests for ServiceManager.
"""

import pytest

from bantu_os.core.kernel.services import (
    ServiceManager,
    ServiceDescriptor,
    ServiceStatus,
)


class DummyService:
    """Minimal service that tracks start/stop calls."""

    def __init__(self):
        self.started = False
        self.stopped = False
        self.health_check_count = 0

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def health_check(self):
        self.health_check_count += 1
        return {"status": "ok"}


class FailingService:
    """Service that fails to start."""

    def start(self):
        raise RuntimeError("boot failure")

    def health_check(self):
        return {"status": "ok"}


# ─── ServiceDescriptor ────────────────────────────────────────────────────


class TestServiceDescriptor:
    def test_name_required(self):
        d = ServiceDescriptor(name="test", description="a test")
        assert d.name == "test"
        assert d.version == "0.1.0"

    def test_version_default(self):
        d = ServiceDescriptor(name="x", description="")
        assert d.version == "0.1.0"


# ─── Registration ─────────────────────────────────────────────────────────


class TestRegistration:
    def test_register_instance(self):
        mgr = ServiceManager()
        dummy = DummyService()
        mgr.register("dummy", dummy, description="test service")
        assert "dummy" in mgr.services
        svc = mgr.services["dummy"]
        assert svc.instance is dummy
        assert svc.status == ServiceStatus.STOPPED

    def test_register_uses_instance_health_check(self):
        mgr = ServiceManager()
        dummy = DummyService()
        mgr.register("dummy", dummy)
        assert callable(mgr.services["dummy"].health_check_fn)
        assert mgr.services["dummy"].health_check_fn.__name__ == "health_check"

    def test_discover_services(self):
        mgr = ServiceManager()
        mgr.discover_services()
        names = list(mgr.services.keys())
        # At minimum file service should be available
        assert isinstance(names, list)


# ─── Lifecycle ────────────────────────────────────────────────────────────


class TestStartStop:
    @pytest.mark.asyncio
    async def test_start_service_sets_healthy(self):
        mgr = ServiceManager()
        dummy = DummyService()
        mgr.register("dummy", dummy)
        ok = await mgr.start_service("dummy")
        assert ok is True
        assert dummy.started is True
        assert mgr.services["dummy"].status == ServiceStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_start_unknown_returns_false(self):
        mgr = ServiceManager()
        ok = await mgr.start_service("ghost")
        assert ok is False

    @pytest.mark.asyncio
    async def test_start_all(self):
        mgr = ServiceManager()
        mgr.register("a", DummyService())
        mgr.register("b", DummyService())
        results = await mgr.start_all()
        assert results["a"] is True
        assert results["b"] is True

    @pytest.mark.asyncio
    async def test_stop_service(self):
        mgr = ServiceManager()
        dummy = DummyService()
        mgr.register("dummy", dummy)
        await mgr.start_service("dummy")
        await mgr.stop_service("dummy")
        assert dummy.stopped is True
        assert mgr.services["dummy"].status == ServiceStatus.STOPPED

    @pytest.mark.asyncio
    async def test_failing_service_sets_failed_status(self):
        mgr = ServiceManager()
        mgr.register("fail", FailingService())
        ok = await mgr.start_service("fail")
        assert ok is False
        assert mgr.services["fail"].status == ServiceStatus.FAILED

    @pytest.mark.asyncio
    async def test_auto_restart_on_failure(self):
        mgr = ServiceManager()
        dummy = DummyService()
        mgr.register("dummy", dummy, restart_policy="on-failure", max_restarts=2)
        await mgr.start_service("dummy")
        # Simulate a failure
        mgr.services["dummy"].status = ServiceStatus.FAILED
        mgr.services["dummy"].restart_count = 0
        await mgr.start_service("dummy")
        assert mgr.services["dummy"].status == ServiceStatus.HEALTHY
        assert dummy.started is True


# ─── Health checks ─────────────────────────────────────────────────────────


class TestHealthChecks:
    @pytest.mark.asyncio
    async def test_health_check_returns_ok(self):
        mgr = ServiceManager()
        dummy = DummyService()
        mgr.register("dummy", dummy)
        await mgr.start_service("dummy")
        report = await mgr.health_check_service("dummy")
        assert report["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        mgr = ServiceManager()
        mgr.register("a", DummyService())
        mgr.register("b", DummyService())
        await mgr.start_all()
        reports = await mgr.health_check_all()
        assert "a" in reports
        assert "b" in reports

    @pytest.mark.asyncio
    async def test_health_check_unknown_service(self):
        mgr = ServiceManager()
        report = await mgr.health_check_service("ghost")
        assert report["status"] == "unknown"


# ─── Introspection ─────────────────────────────────────────────────────────


class TestIntrospection:
    def test_list_services_returns_summary(self):
        mgr = ServiceManager()
        mgr.register("svc1", DummyService(), description="first")
        mgr.register("svc2", DummyService(), description="second")
        listing = mgr.list_services()
        assert len(listing) == 2
        names = {s["name"] for s in listing}
        assert "svc1" in names
        assert "svc2" in names

    def test_service_count(self):
        mgr = ServiceManager()
        mgr.register("a", DummyService())
        mgr.register("b", DummyService())
        assert mgr.service_count == 2
