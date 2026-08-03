# pyright: reportMissingTypeStubs=false

"""
IoTService — Phase 3.

MQTT-based IoT device management and sensor data ingestion.
Supports any MQTT-compatible device (ESP32, Raspberry Pi, sensors, etc.)

Exposes tools to the Bantu-OS kernel via `use_tool_async`:

    iot_publish_message     — publish a message to an MQTT topic
    iot_subscribe           — subscribe to an MQTT topic and receive messages
    iot_list_devices        — list all registered IoT devices
    iot_register_device     — register a new IoT device
    iot_get_device_status   — get the status of a registered device
    iot_ingest_sensor_data  — ingest sensor readings into the time-series store

Env vars required:
    MQTT_BROKER_URL         MQTT broker URL (e.g. mosquitto://localhost:1883)
    MQTT_USERNAME           MQTT username (optional)
    MQTT_PASSWORD           MQTT password (optional)
    MQTT_CLIENT_ID          Unique client identifier (defaults to bantu-iot-{hostname})

Supported QoS levels:
    0 — at most once (fire and forget)
    1 — at least once (acknowledged delivery)
    2 — exactly once (assured delivery)

Usage:
    from bantu_os.services.iot import IoTService

    svc = IoTService()
    result = await svc.use_tool_async(
        'iot_publish_message',
        {'topic': 'home/sensors/temperature', 'payload': '23.5', 'qos': 1}
    )
"""

from __future__ import annotations


import asyncio
import os
import time
from urllib.parse import urlparse
from typing import Any, Dict, Optional

from bantu_os.services.service_base import ServiceBase

# Optional: paho-mqtt for actual MQTT support
try:
    import paho.mqtt.client as mqtt

    _MQTT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _MQTT_AVAILABLE = False
    mqtt = None


# ─── Device Registry (in-memory for Phase 3, upgrade to SQLite later) ────────

_DEVICE_REGISTRY: Dict[str, Dict[str, Any]] = {}


def _register_device(
    device_id: str, name: str, device_type: str, metadata: Dict[str, Any]
) -> None:
    _DEVICE_REGISTRY[device_id] = {
        "device_id": device_id,
        "name": name,
        "type": device_type,
        "metadata": metadata,
        "registered_at": time.time(),
        "last_seen": None,
        "status": "offline",
    }


def _device_status(device_id: str) -> Optional[Dict[str, Any]]:
    return _DEVICE_REGISTRY.get(device_id)


# ─── Sensor Data Store (simple in-memory time-series for Phase 3) ───────────

_SENSOR_STORE: Dict[str, list] = {}


def _ingest_reading(
    device_id: str, sensor_type: str, value: Any, unit: str
) -> Dict[str, Any]:
    ts = time.time()
    entry = {
        "ts": ts,
        "device_id": device_id,
        "type": sensor_type,
        "value": value,
        "unit": unit,
    }
    key = f"{device_id}:{sensor_type}"
    if key not in _SENSOR_STORE:
        _SENSOR_STORE[key] = []
    _SENSOR_STORE[key].append(entry)
    # Keep last 1000 readings per sensor
    if len(_SENSOR_STORE[key]) > 1000:
        _SENSOR_STORE[key] = _SENSOR_STORE[key][-1000:]
    # Update device last_seen
    if device_id in _DEVICE_REGISTRY:
        _DEVICE_REGISTRY[device_id]["last_seen"] = ts
        _DEVICE_REGISTRY[device_id]["status"] = "online"
    return entry


# ─── MQTT Client Wrapper ─────────────────────────────────────────────────────


class _MQTTClient:
    """Lightweight MQTT client wrapper using paho-mqtt."""

    def __init__(
        self,
        broker_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> None:
        if not _MQTT_AVAILABLE:
            raise OSError("paho-mqtt not installed. Run: pip install paho-mqtt")

        parsed = urlparse(broker_url)
        if parsed.scheme not in {"mqtt", "mqtts"} or not parsed.hostname:
            raise ValueError("MQTT_BROKER_URL must use mqtt:// or mqtts:// with a host")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError(
                "MQTT_BROKER_URL must not include a path, query, or fragment"
            )
        if parsed.username or parsed.password:
            raise ValueError("MQTT_BROKER_URL must not contain credentials")
        self._broker = broker_url
        self._connected = False
        self._client = mqtt.Client(
            client_id=client_id or f"bantu-iot-{os.uname().nodename}",
            clean_session=True,
        )
        if bool(username) != bool(password):
            raise ValueError(
                "MQTT_USERNAME and MQTT_PASSWORD must be provided together"
            )
        if username and password:
            self._client.username_pw_set(username, password)
        if parsed.scheme == "mqtts":
            self._client.tls_set()

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._messages: Dict[str, list] = {}

    def _on_connect(self, client, userdata, flags, rc) -> None:
        self._connected = rc == 0

    def _on_disconnect(self, client, userdata, rc) -> None:
        self._connected = False

    def connect(self, timeout: float = 5.0) -> None:
        parsed = urlparse(self._broker)
        host = parsed.hostname
        port = parsed.port or (8883 if parsed.scheme == "mqtts" else 1883)
        if not host or not 1 <= port <= 65535:
            raise ValueError("MQTT_BROKER_URL contains an invalid host or port")
        if timeout <= 0:
            raise ValueError("MQTT connection timeout must be positive")
        self._client.connect_timeout = float(timeout)
        self._client.loop_start()
        try:
            rc = self._client.connect(host, port)
            if rc != mqtt.MQTT_ERR_SUCCESS:
                raise OSError(f"MQTT connection rejected with return code {rc}")
        except Exception:
            self._client.loop_stop()
            raise
        deadline = time.monotonic() + timeout
        while not self._connected and time.monotonic() < deadline:
            time.sleep(0.01)
        if not self._connected:
            self._client.loop_stop()
            raise TimeoutError(
                "MQTT broker did not accept the connection before timeout"
            )

    def disconnect(self) -> None:
        self._client.disconnect()
        self._client.loop_stop()

    @property
    def is_connected(self) -> bool:
        return self._connected

    def publish(self, topic: str, payload: str, qos: int = 0) -> Dict[str, Any]:
        if not self._connected:
            raise OSError("MQTT client not connected. Call connect() first.")
        info = self._client.publish(topic, payload.encode(), qos=qos)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise OSError(f"MQTT publish rejected with return code {info.rc}")
        return {"mid": info.mid, "rc": info.rc, "topic": topic}

    def subscribe(self, topic: str, qos: int = 0) -> None:
        if not self._connected:
            raise OSError("MQTT client not connected. Call connect() first.")
        self._client.subscribe(topic, qos)
        if topic not in self._messages:
            self._messages[topic] = []

    def get_messages(self, topic: str) -> list:
        return self._messages.get(topic, [])

    def on_message(self, client, userdata, msg) -> None:
        topic = msg.topic
        if topic not in self._messages:
            self._messages[topic] = []
        self._messages[topic].append(
            {"payload": msg.payload.decode(), "qos": msg.qos, "ts": time.time()}
        )


# ─── Service ─────────────────────────────────────────────────────────────────


class IoTService(ServiceBase):
    """
    MQTT-based IoT device management and sensor data ingestion.

    Devices are registered in an in-memory registry. Sensor readings are
    buffered in a simple time-series store (upgrade to proper TSDB later).
    """

    def __init__(self) -> None:
        super().__init__(name="iot")
        self._client: Optional[_MQTTClient] = None

    # ─── MQTT connection ──────────────────────────────────────────────────────

    def _get_client(self) -> _MQTTClient:
        if self._client is None:
            broker = os.environ.get("MQTT_BROKER_URL", "mqtt://localhost:1883")
            username = os.environ.get("MQTT_USERNAME") or None
            password = os.environ.get("MQTT_PASSWORD") or None
            client_id = os.environ.get("MQTT_CLIENT_ID") or None
            self._client = _MQTTClient(broker, username, password, client_id)
        return self._client

    def health_check(self) -> Dict[str, Any]:
        try:
            client = self._get_client()
            return {
                "status": "ok" if client.is_connected else "degraded",
                "service": self.name,
                "mqtt_broker": os.environ.get(
                    "MQTT_BROKER_URL", "mqtt://localhost:1883"
                ),
                "connected": client.is_connected,
                "devices_registered": len(_DEVICE_REGISTRY),
            }
        except (OSError, ValueError) as e:
            return {"status": "degraded", "service": self.name, "error": str(e)}

    @property
    def tool_schema(self) -> Dict[str, Any]:
        from bantu_os.services.iot import schemas as _schemas

        return _schemas.TOOL_SCHEMAS

    async def use_tool_async(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        dispatch = {
            "iot_publish_message": self.iot_publish_message,
            "iot_subscribe": self.iot_subscribe,
            "iot_list_devices": self.iot_list_devices,
            "iot_register_device": self.iot_register_device,
            "iot_get_device_status": self.iot_get_device_status,
            "iot_ingest_sensor_data": self.iot_ingest_sensor_data,
        }
        if tool_name not in dispatch:
            raise ValueError(f"[IoTService] Unknown tool: {tool_name!r}")
        return await dispatch[tool_name](**params)

    # ─── Tools ───────────────────────────────────────────────────────────────

    async def iot_publish_message(
        self,
        topic: str,
        payload: str,
        qos: int = 0,
    ) -> Dict[str, Any]:
        """
        Publish a message to an MQTT topic.

        Args:
            topic:    MQTT topic string (e.g. ``home/sensors/temperature``)
            payload:  Message content (string or JSON)
            qos:      Quality of Service level (0, 1, or 2)

        Returns:
            ``{'mid': <int>, 'rc': <int>, 'topic': <str>}``
        """
        if (
            not isinstance(topic, str)
            or not topic.strip()
            or "#" in topic
            or "+" in topic
        ):
            raise ValueError(
                "topic must be a non-empty publish topic without wildcards"
            )
        if not isinstance(payload, str):
            raise ValueError("payload must be a string")
        if qos not in {0, 1, 2}:
            raise ValueError("qos must be 0, 1, or 2")
        if not _MQTT_AVAILABLE:
            raise OSError("paho-mqtt is not installed. Run: pip install paho-mqtt")
        try:
            client = self._get_client()
            if not client.is_connected:
                await asyncio.to_thread(client.connect)
            return client.publish(topic, payload, qos=qos)
        except Exception as e:
            raise OSError(f"MQTT publish failed: {e}") from e

    async def iot_subscribe(
        self,
        topic: str,
        qos: int = 0,
        timeout: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Subscribe to an MQTT topic and collect messages for ``timeout`` seconds.

        Args:
            topic:    MQTT topic to subscribe to (supports wildcards: ``home/#``)
            qos:      Quality of Service level (0, 1, or 2)
            timeout:  Seconds to collect messages before returning

        Returns:
            ``{'topic': <str>, 'messages': [...], 'count': <int>}``
        """
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("topic must be a non-empty string")
        if "\x00" in topic:
            raise ValueError("topic must not contain NUL characters")
        if qos not in {0, 1, 2}:
            raise ValueError("qos must be 0, 1, or 2")
        if not isinstance(timeout, (int, float)) or not 0 < timeout <= 300:
            raise ValueError("timeout must be greater than 0 and at most 300 seconds")
        if not _MQTT_AVAILABLE:
            raise OSError("paho-mqtt is not installed. Run: pip install paho-mqtt")
        try:
            client = self._get_client()
            if not client.is_connected:
                await asyncio.to_thread(client.connect)
            client.subscribe(topic, qos=qos)
            client._client.on_message = client.on_message
            await asyncio.sleep(timeout)
            messages = client.get_messages(topic)
            return {"topic": topic, "messages": messages, "count": len(messages)}
        except Exception as e:
            raise OSError(f"MQTT subscribe failed: {e}") from e

    async def iot_list_devices(self) -> Dict[str, Any]:
        """
        List all registered IoT devices.

        Returns:
            ``{'devices': [...], 'count': <int>}``
        """
        devices = list(_DEVICE_REGISTRY.values())
        return {"devices": devices, "count": len(devices)}

    async def iot_register_device(
        self,
        device_id: str,
        name: str,
        device_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Register a new IoT device with Bantu-OS.

        Args:
            device_id:   Unique device identifier (e.g. ``esp32-001``)
            name:        Human-readable device name (e.g. ``Kitchen Sensor``)
            device_type: Type of device (e.g. ``temperature_sensor``, ``motion_detector``)
            metadata:    Optional key-value metadata

        Returns:
            ``{'registered': True, 'device_id': <str>}``
        """
        _register_device(device_id, name, device_type, metadata or {})
        return {"registered": True, "device_id": device_id}

    async def iot_get_device_status(
        self,
        device_id: str,
    ) -> Dict[str, Any]:
        """
        Get the current status of a registered device.

        Args:
            device_id: Unique device identifier

        Returns:
            Device status dict, or ``{'error': 'Device not found'}``
        """
        device = _device_status(device_id)
        if device is None:
            return {"error": f"Device '{device_id}' not found"}
        return device

    async def iot_ingest_sensor_data(
        self,
        device_id: str,
        sensor_type: str,
        value: Any,
        unit: str = "",
    ) -> Dict[str, Any]:
        """
        Ingest a sensor reading into the time-series store.

        Args:
            device_id:   ID of the device taking the reading
            sensor_type: Type of measurement (e.g. ``temperature``, ``humidity``, ``pressure``)
            value:        Measured value (number or string)
            unit:         Unit of measurement (e.g. ``°C``, ``%``, ``hPa``)

        Returns:
            ``{'stored': True, 'ts': <float>, 'key': '<device_id>:<sensor_type>'}``
        """
        entry = _ingest_reading(device_id, sensor_type, value, unit)
        return {"stored": True, "ts": entry["ts"], "key": f"{device_id}:{sensor_type}"}
