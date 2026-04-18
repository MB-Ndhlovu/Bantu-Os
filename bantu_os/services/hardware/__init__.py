# pyright: reportMissingTypeStubs=false

"""
HardwareService — Phase 3.

Hardware abstraction layer for Bantu-OS. Provides a consistent interface
for reading sensors, controlling actuators, and monitoring system hardware
(Raspberry Pi GPIO, USB devices, CPU stats, disk, network interfaces).

Exposes tools via ``use_tool_async``:

    hardware_cpu_stats       — CPU usage, temperature, frequency
    hardware_memory_stats    — RAM and swap usage
    hardware_disk_usage     — disk space per mount point
    hardware_network_stats   — network interface RX/TX bytes
    hardware_gpio_read       — read a GPIO pin (Raspberry Pi)
    hardware_gpio_write       — set a GPIO pin HIGH or LOW
    hardware_usb_list        — list connected USB devices

Usage:
    from bantu_os.services.hardware import HardwareService

    svc = HardwareService()
    result = await svc.use_tool_async('hardware_cpu_stats', {})
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    psutil = None
    _PSUTIL_AVAILABLE = False

try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except ImportError:  # pragma: no cover
    GPIO = None
    _GPIO_AVAILABLE = False

from bantu_os.services.service_base import ServiceBase


class HardwareService(ServiceBase):
    """
    Hardware abstraction layer for system monitoring and device control.

    Covers:
    - CPU, memory, disk, network (via psutil)
    - GPIO pins (via RPi.GPIO — Raspberry Pi)
    - USB device enumeration
    """

    def __init__(self) -> None:
        super().__init__(name="hardware")

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "service": self.name,
            "psutil": _PSUTIL_AVAILABLE,
            "gpio": _GPIO_AVAILABLE,
        }

    @property
    def tool_schema(self) -> Dict[str, Any]:
        from bantu_os.services.hardware import schemas as _schemas
        return _schemas.TOOL_SCHEMAS

    async def use_tool_async(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        dispatch = {
            "hardware_cpu_stats": self.hardware_cpu_stats,
            "hardware_memory_stats": self.hardware_memory_stats,
            "hardware_disk_usage": self.hardware_disk_usage,
            "hardware_network_stats": self.hardware_network_stats,
            "hardware_gpio_read": self.hardware_gpio_read,
            "hardware_gpio_write": self.hardware_gpio_write,
            "hardware_usb_list": self.hardware_usb_list,
        }
        if tool_name not in dispatch:
            raise ValueError(f"[HardwareService] Unknown tool: {tool_name!r}")
        return await dispatch[tool_name](**params)

    # ─── CPU ───────────────────────────────────────────────────────────────

    async def hardware_cpu_stats(self) -> Dict[str, Any]:
        """
        Get CPU usage, temperature, and frequency.

        Returns:
            ``{'cpu_percent': <float>, 'temperature': <float|None>, 'frequency_mhz': <float>,
               'core_count': <int>, 'uptime_seconds': <float>}``
        """
        if not _PSUTIL_AVAILABLE:
            raise OSError("psutil not installed. Run: pip install psutil")

        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count()
        freq = psutil.cpu_freq()
        temp = None
        # Try temperature on Linux (thermal_zone)
        for path in ("/sys/class/thermal/thermal_zone0/temp", "/proc/acpi/thermal_zone/TZ00/temperature"):
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        temp = int(f.read().strip()) / 1000.0
                    break
                except (OSError, ValueError):
                    pass
        # Raspberry Pi BCM GPIO temperature
        if temp is None and os.path.exists("/opt/vc/bin/vcgencmd"):
            import subprocess
            try:
                out = subprocess.check_output(
                    ["/opt/vc/bin/vcgencmd", "measure_temp"],
                    text=True
                )
                temp = float(out.replace("temp=", "").replace("'C\n", ""))
            except (OSError, ValueError):
                pass

        uptime = time.time() - psutil.boot_time()
        return {
            "cpu_percent": cpu_percent,
            "temperature_c": temp,
            "frequency_mhz": freq.current if freq else None,
            "core_count": cpu_count,
            "uptime_seconds": uptime,
        }

    # ─── Memory ──────────────────────────────────────────────────────────

    async def hardware_memory_stats(self) -> Dict[str, Any]:
        """
        Get RAM and swap usage.

        Returns:
            ``{'ram_total_b': <int>, 'ram_used_b': <int>, 'ram_percent': <float>,
               'swap_total_b': <int>, 'swap_used_b': <int>, 'swap_percent': <float>}``
        """
        if not _PSUTIL_AVAILABLE:
            raise OSError("psutil not installed. Run: pip install psutil")
        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()
        return {
            "ram_total_b": vm.total,
            "ram_used_b": vm.used,
            "ram_percent": vm.percent,
            "ram_free_b": vm.available,
            "swap_total_b": sm.total,
            "swap_used_b": sm.used,
            "swap_percent": sm.percent,
        }

    # ─── Disk ────────────────────────────────────────────────────────────

    async def hardware_disk_usage(self, mount_point: str = "/") -> Dict[str, Any]:
        """
        Get disk usage for a mount point.

        Args:
            mount_point: Filesystem mount point. Defaults to ``/``.

        Returns:
            ``{'total_b': <int>, 'used_b': <int>, 'free_b': <int>, 'percent': <float>}``
        """
        if not _PSUTIL_AVAILABLE:
            raise OSError("psutil not installed. Run: pip install psutil")
        usage = psutil.disk_usage(mount_point)
        return {
            "mount_point": mount_point,
            "total_b": usage.total,
            "used_b": usage.used,
            "free_b": usage.free,
            "percent": usage.percent,
        }

    # ─── Network ────────────────────────────────────────────────────────

    async def hardware_network_stats(self, interface: str = "eth0") -> Dict[str, Any]:
        """
        Get network interface RX/TX statistics.

        Args:
            interface: Network interface name (e.g. ``eth0``, ``wlan0``, ``lo``).
                       Defaults to ``eth0``.

        Returns:
            ``{'interface': <str>, 'bytes_recv': <int>, 'bytes_sent': <int>,
               'packets_recv': <int>, 'packets_sent': <int>, 'errin': <int>, 'errout': <int>}``
        """
        if not _PSUTIL_AVAILABLE:
            raise OSError("psutil not installed. Run: pip install psutil")
        counters = psutil.net_io_counters(pernic=True).get(interface)
        if counters is None:
            return {"error": f"Interface '{interface}' not found", "available": list(psutil.net_io_counters(pernic=True).keys())}
        return {
            "interface": interface,
            "bytes_recv": counters.bytes_recv,
            "bytes_sent": counters.bytes_sent,
            "packets_recv": counters.packets_recv,
            "packets_sent": counters.packets_sent,
            "errin": counters.errin,
            "errout": counters.errout,
        }

    # ─── GPIO ───────────────────────────────────────────────────────────

    async def hardware_gpio_read(self, pin: int) -> Dict[str, Any]:
        """
        Read the state of a GPIO pin (Raspberry Pi).

        Args:
            pin: BCM GPIO pin number (e.g. ``17`` for GPIO 17).

        Returns:
            ``{'pin': <int>, 'state': 0|1, 'mode': 'BCM'}``
        """
        if not _GPIO_AVAILABLE:
            raise OSError("RPi.GPIO not available. This tool only works on Raspberry Pi.")
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.IN)
            state = GPIO.input(pin)
            return {"pin": pin, "state": state, "mode": "BCM"}
        except Exception as e:
            raise OSError(f"GPIO read failed on pin {pin}: {e}")

    async def hardware_gpio_write(self, pin: int, state: bool) -> Dict[str, Any]:
        """
        Set a GPIO pin HIGH or LOW (Raspberry Pi).

        Args:
            pin:   BCM GPIO pin number.
            state: ``True`` for HIGH (3.3V), ``False`` for LOW (0V).

        Returns:
            ``{'pin': <int>, 'state': 0|1}``
        """
        if not _GPIO_AVAILABLE:
            raise OSError("RPi.GPIO not available. This tool only works on Raspberry Pi.")
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
            return {"pin": pin, "state": 1 if state else 0}
        except Exception as e:
            raise OSError(f"GPIO write failed on pin {pin}: {e}")

    # ─── USB ────────────────────────────────────────────────────────────

    async def hardware_usb_list(self) -> Dict[str, Any]:
        """
        List all connected USB devices.

        Returns:
            ``{'devices': [...], 'count': <int>}``
        """
        devices = []
        usb_path = "/sys/bus/usb/devices"
        if os.path.exists(usb_path):
            for name in os.listdir(usb_path):
                dev_path = os.path.join(usb_path, name)
                id_vendor = ""
                id_product = ""
                manufacturer = ""
                try:
                    for k, fname in [
                        ("idVendor", "idVendor"),
                        ("idProduct", "idProduct"),
                        ("manufacturer", "manufacturer"),
                    ]:
                        p = os.path.join(dev_path, fname)
                        if os.path.exists(p):
                            with open(p) as f:
                                if k == "idVendor":
                                    id_vendor = f.read().strip()
                                elif k == "idProduct":
                                    id_product = f.read().strip()
                                else:
                                    manufacturer = f.read().strip()
                    if id_vendor:
                        devices.append({
                            "bus": name,
                            "vendor_id": id_vendor,
                            "product_id": id_product,
                            "manufacturer": manufacturer,
                        })
                except OSError:
                    pass
        return {"devices": devices, "count": len(devices)}