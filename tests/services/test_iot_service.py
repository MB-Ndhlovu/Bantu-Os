"""
Tests for IoTService.
"""
import pytest

pytestmark = pytest.mark.asyncio


class TestIoTService:
    async def test_register_and_list_device(self):
        from bantu_os.services.iot import IoTService
        svc = IoTService()
        await svc.iot_register_device("esp32-001", "Kitchen Sensor", "temperature_sensor", {"location": "kitchen"})
        result = await svc.iot_list_devices()
        assert result["count"] >= 1
        assert any(d["device_id"] == "esp32-001" for d in result["devices"])

    async def test_get_device_status_found(self):
        from bantu_os.services.iot import IoTService
        svc = IoTService()
        await svc.iot_register_device("pi-001", "RPi Gateway", "gateway", {})
        result = await svc.iot_get_device_status("pi-001")
        assert "error" not in result
        assert result["device_id"] == "pi-001"
        assert result["status"] == "offline"

    async def test_get_device_status_not_found(self):
        from bantu_os.services.iot import IoTService
        svc = IoTService()
        result = await svc.iot_get_device_status("ghost-device")
        assert "error" in result

    async def test_ingest_sensor_data(self):
        from bantu_os.services.iot import IoTService
        svc = IoTService()
        result = await svc.iot_ingest_sensor_data("esp32-001", "temperature", 23.5, "°C")
        assert result["stored"] is True
        assert "ts" in result
        assert result["key"] == "esp32-001:temperature"

    async def test_publish_requires_mqtt_library(self):
        from bantu_os.services.iot import IoTService
        svc = IoTService()
        # Will raise OSError because MQTT_BROKER_URL is not set
        # and we're not in a real MQTT environment
        with pytest.raises(OSError, match="MQTT"):
            await svc.iot_publish_message("home/test", "hello", qos=0)

    async def test_tool_schema_has_all_tools(self):
        from bantu_os.services.iot import IoTService
        svc = IoTService()
        schema = svc.tool_schema
        expected = [
            "iot_publish_message",
            "iot_subscribe",
            "iot_list_devices",
            "iot_register_device",
            "iot_get_device_status",
            "iot_ingest_sensor_data",
        ]
        for tool in expected:
            assert tool in schema, f"{tool} missing from schema"

    async def test_unknown_tool_raises(self):
        from bantu_os.services.iot import IoTService
        svc = IoTService()
        with pytest.raises(ValueError, match="Unknown tool"):
            await svc.use_tool_async("unknown_tool", {})