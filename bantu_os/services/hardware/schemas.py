"""
HardwareService tool schemas — Phase 3.
"""
from __future__ import annotations

TOOL_SCHEMAS = {
    "hardware_cpu_stats": {
        "description": "Get CPU usage, temperature, and frequency for the host system.",
        "parameters": {"type": "object", "properties": {}},
        "returns": {
            "type": "object",
            "properties": {
                "cpu_percent": {"type": "number"},
                "temperature_c": {"type": "number"},
                "frequency_mhz": {"type": "number"},
                "core_count": {"type": "integer"},
                "uptime_seconds": {"type": "number"},
            },
        },
    },
    "hardware_memory_stats": {
        "description": "Get RAM and swap usage for the host system.",
        "parameters": {"type": "object", "properties": {}},
        "returns": {
            "type": "object",
            "properties": {
                "ram_total_b": {"type": "integer"},
                "ram_used_b": {"type": "integer"},
                "ram_percent": {"type": "number"},
                "ram_free_b": {"type": "integer"},
                "swap_total_b": {"type": "integer"},
                "swap_used_b": {"type": "integer"},
                "swap_percent": {"type": "number"},
            },
        },
    },
    "hardware_disk_usage": {
        "description": "Get disk usage for a filesystem mount point.",
        "parameters": {
            "type": "object",
            "properties": {"mount_point": {"type": "string", "default": "/"}},
        },
        "returns": {
            "type": "object",
            "properties": {
                "mount_point": {"type": "string"},
                "total_b": {"type": "integer"},
                "used_b": {"type": "integer"},
                "free_b": {"type": "integer"},
                "percent": {"type": "number"},
            },
        },
    },
    "hardware_network_stats": {
        "description": "Get network interface RX/TX statistics.",
        "parameters": {
            "type": "object",
            "properties": {"interface": {"type": "string", "default": "eth0"}},
        },
        "returns": {
            "type": "object",
            "properties": {
                "interface": {"type": "string"},
                "bytes_recv": {"type": "integer"},
                "bytes_sent": {"type": "integer"},
                "packets_recv": {"type": "integer"},
                "packets_sent": {"type": "integer"},
            },
        },
    },
    "hardware_gpio_read": {
        "description": "Read the state of a GPIO pin (Raspberry Pi BCM numbering).",
        "parameters": {
            "type": "object",
            "properties": {"pin": {"type": "integer", "description": "BCM GPIO pin number (e.g. 17)"}},
            "required": ["pin"],
        },
        "returns": {
            "type": "object",
            "properties": {"pin": {"type": "integer"}, "state": {"type": "integer"}, "mode": {"type": "string"}},
        },
    },
    "hardware_gpio_write": {
        "description": "Set a GPIO pin HIGH or LOW (Raspberry Pi BCM numbering).",
        "parameters": {
            "type": "object",
            "properties": {
                "pin": {"type": "integer"},
                "state": {"type": "boolean", "description": "True = HIGH (3.3V), False = LOW (0V)"},
            },
            "required": ["pin", "state"],
        },
        "returns": {"type": "object", "properties": {"pin": {"type": "integer"}, "state": {"type": "integer"}}},
    },
    "hardware_usb_list": {
        "description": "List all connected USB devices on the host.",
        "parameters": {"type": "object", "properties": {}},
        "returns": {
            "type": "object",
            "properties": {"devices": {"type": "array"}, "count": {"type": "integer"}},
        },
    },
}