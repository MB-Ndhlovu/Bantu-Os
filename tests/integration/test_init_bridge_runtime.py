from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path

from bantu_os.core.init_bridge import InitBridge


def _wait_for_socket(path: Path, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.02)
    raise AssertionError(f"registry socket did not appear: {path}")


def _request(path: Path, payload: dict) -> dict:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(str(path))
        client.sendall((json.dumps(payload) + "\n").encode())
        return json.loads(client.recv(4096).decode())


def test_python_bridge_registers_heartbeats_and_unregisters(tmp_path: Path) -> None:
    socket_path = tmp_path / "init.sock"
    source_root = Path(__file__).resolve().parents[2]
    binary = tmp_path / "bantu-init"
    subprocess.run(
        [
            "gcc",
            "-Wall",
            "-Wextra",
            "-std=c11",
            str(source_root / "init/init.c"),
            str(source_root / "init/services.c"),
            str(source_root / "init/registry_socket.c"),
            "-o",
            str(binary),
        ],
        check=True,
    )
    env = os.environ.copy()
    env["BANTU_INIT_REGISTRY_SOCKET"] = str(socket_path)
    env["BANTU_INIT_SHELL_PATH"] = "/bin/true"
    env["BANTU_INIT_SKIP_MOUNTS"] = "1"
    process = subprocess.Popen(
        [str(binary)],
        cwd=source_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        _wait_for_socket(socket_path)
        bridge = InitBridge(service_name="runtime-test", socket_path=str(socket_path))
        assert bridge.register() is True
        assert bridge.heartbeat() is True
        status = bridge.get_service_status("runtime-test")
        assert status is not None
        assert status["name"] == "runtime-test"
        assert status["state"].lower() == "running"
        bridge.unregister()
        status = _request(socket_path, {"cmd": "status", "name": "runtime-test"})
        assert status["ok"] is True
        assert status["state"].lower() == "stopped"
    finally:
        os.killpg(process.pid, __import__("signal").SIGTERM)
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
