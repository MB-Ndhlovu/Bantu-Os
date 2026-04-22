"""
IoTService tool schemas — Phase 3.
"""

from __future__ import annotations

TOOL_SCHEMAS = {
    "iot_publish_message": {
        "description": "Publish a message to an MQTT topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "MQTT topic string (e.g. home/sensors/temperature). Supports wildcards.",
                },
                "payload": {
                    "type": "string",
                    "description": "Message content — string or JSON.",
                },
                "qos": {
                    "type": "integer",
                    "description": "Quality of Service: 0 (at most once), 1 (at least once), 2 (exactly once).",
                    "default": 0,
                },
            },
            "required": ["topic", "payload"],
        },
        "returns": {
            "type": "object",
            "properties": {
                "mid": {"type": "integer", "description": "MQTT message ID."},
                "rc": {"type": "integer", "description": "Return code (0 = success)."},
                "topic": {"type": "string"},
            },
        },
    },
    "iot_subscribe": {
        "description": "Subscribe to an MQTT topic and collect messages for a period.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "MQTT topic (supports wildcards like home/#).",
                },
                "qos": {"type": "integer", "default": 0},
                "timeout": {
                    "type": "number",
                    "description": "Seconds to collect messages before returning.",
                    "default": 5.0,
                },
            },
            "required": ["topic"],
        },
        "returns": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "messages": {
                    "type": "array",
                    "description": "List of received messages.",
                },
                "count": {"type": "integer"},
            },
        },
    },
    "iot_list_devices": {
        "description": "List all registered IoT devices.",
        "parameters": {"type": "object", "properties": {}},
        "returns": {
            "type": "object",
            "properties": {"devices": {"type": "array"}, "count": {"type": "integer"}},
        },
    },
    "iot_register_device": {
        "description": "Register a new IoT device with Bantu-OS.",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "Unique device identifier.",
                },
                "name": {
                    "type": "string",
                    "description": "Human-readable device name.",
                },
                "device_type": {
                    "type": "string",
                    "description": "Device type (e.g. temperature_sensor, motion_detector).",
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional key-value metadata.",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["device_id", "name", "device_type"],
        },
        "returns": {
            "type": "object",
            "properties": {
                "registered": {"type": "boolean"},
                "device_id": {"type": "string"},
            },
        },
    },
    "iot_get_device_status": {
        "description": "Get the current status of a registered device.",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "Unique device identifier.",
                }
            },
            "required": ["device_id"],
        },
        "returns": {"type": "object"},
    },
    "iot_ingest_sensor_data": {
        "description": "Ingest a sensor reading into the time-series store.",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string"},
                "sensor_type": {
                    "type": "string",
                    "description": "e.g. temperature, humidity",
                },
                "value": {"type": "number"},
                "unit": {"type": "string", "description": "e.g. °C, %, hPa"},
            },
            "required": ["device_id", "sensor_type", "value"],
        },
        "returns": {
            "type": "object",
            "properties": {
                "stored": {"type": "boolean"},
                "ts": {"type": "number"},
                "key": {"type": "string"},
            },
        },
    },
}
