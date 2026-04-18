"""
Tests for HardwareService.
"""
import pytest

pytestmark = pytest.mark.asyncio


class TestHardwareService:
    async def test_cpu_stats_returns_fields(self):
        from bantu_os.services.hardware import HardwareService
        svc = HardwareService()
        result = await svc.hardware_cpu_stats()
        assert "cpu_percent" in result
        assert "core_count" in result
        assert "uptime_seconds" in result

    async def test_memory_stats_returns_fields(self):
        from bantu_os.services.hardware import HardwareService
        svc = HardwareService()
        result = await svc.hardware_memory_stats()
        assert "ram_total_b" in result
        assert "ram_used_b" in result
        assert "ram_percent" in result
        assert "swap_total_b" in result

    async def test_disk_usage_defaults_to_root(self):
        from bantu_os.services.hardware import HardwareService
        svc = HardwareService()
        result = await svc.hardware_disk_usage()
        assert result["mount_point"] == "/"
        assert "total_b" in result
        assert "percent" in result

    async def test_disk_usage_custom_mount_point(self):
        from bantu_os.services.hardware import HardwareService
        svc = HardwareService()
        result = await svc.hardware_disk_usage(mount_point="/tmp")
        assert "total_b" in result

    async def test_network_stats_invalid_interface(self):
        from bantu_os.services.hardware import HardwareService
        svc = HardwareService()
        result = await svc.hardware_network_stats(interface="nonexistent0")
        # Returns error dict when interface not found
        assert "error" in result or "bytes_recv" in result

    async def test_usb_list_returns_devices(self):
        from bantu_os.services.hardware import HardwareService
        svc = HardwareService()
        result = await svc.hardware_usb_list()
        assert "devices" in result
        assert "count" in result
        assert isinstance(result["devices"], list)

    async def test_tool_schema_has_all_tools(self):
        from bantu_os.services.hardware import HardwareService
        svc = HardwareService()
        schema = svc.tool_schema
        expected = [
            "hardware_cpu_stats",
            "hardware_memory_stats",
            "hardware_disk_usage",
            "hardware_network_stats",
            "hardware_gpio_read",
            "hardware_gpio_write",
            "hardware_usb_list",
        ]
        for tool in expected:
            assert tool in schema, f"{tool} missing from schema"

    async def test_unknown_tool_raises(self):
        from bantu_os.services.hardware import HardwareService
        svc = HardwareService()
        with pytest.raises(ValueError, match="Unknown tool"):
            await svc.use_tool_async("unknown_tool", {})