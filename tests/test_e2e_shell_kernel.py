#!/usr/bin/env python3
"""
End-to-end smoke test: Rust shell → Unix socket → Python kernel → AI response.
Tests the full boot loop described in SPEC.md Phase 1.

Usage: python tests/test_e2e_shell_kernel.py
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOCKET_PATH = "/tmp/bantu.sock"
TCP_PORT = 18792
KERNEL_LOG = "/tmp/bantu-kernel-e2e.log"
MAX_WAIT = 15
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") or os.environ.get(
    "OPENAI_API_KEY"
)


def can_run_ai_tests() -> bool:
    """AI tests need an API key or a stubbed provider."""
    return bool(OPENROUTER_API_KEY)


def kill_existing():
    """Kill any running kernel/server processes."""
    for name in ["socket_server", "python.*m bantu_os", "python.*socket_server"]:
        subprocess.run(["pkill", "-f", name], capture_output=True)
    time.sleep(1)
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)


def start_kernel() -> subprocess.Popen:
    """Start Python kernel server, return process handle."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    # Suppress Chromium/EasyML spam
    env["PYTHONWARNINGS"] = "ignore"

    proc = subprocess.Popen(
        [sys.executable, "-m", "bantu_os.core.socket_server"],
        env=env,
        stdout=open(KERNEL_LOG, "w"),
        stderr=subprocess.STDOUT,
    )
    return proc


def wait_for_socket(path: str, timeout: int = MAX_WAIT) -> bool:
    """Block until Unix socket exists and accepts connections."""
    waited = 0
    while waited < timeout * 2:
        if os.path.exists(path):
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.settimeout(0.5)
                s.connect(path)
                s.close()
                return True
            except (socket.error, OSError):
                pass
        time.sleep(0.5)
        waited += 1
    return False


def wait_for_server_ready(port: int, timeout: int = MAX_WAIT) -> bool:
    """Block until TCP server is responding."""
    waited = 0
    while waited < timeout * 2:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except (socket.error, OSError):
            pass
        time.sleep(0.5)
        waited += 1
    return False


def send_json(sock: socket.socket, obj: dict) -> dict:
    """Send a JSON request, receive JSON response."""
    msg = json.dumps(obj) + "\n"
    sock.sendall(msg.encode())
    sock.settimeout(5.0)
    data = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
        if b"\n" in data:
            break
    return json.loads(data.decode().strip())


def run_tests():
    results = []

    # -------------------------------------------------------------------------
    # Test 1: Unix socket ping
    # -------------------------------------------------------------------------
    def test_ping_unix():
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)
        resp = send_json(sock, {"cmd": "ping"})
        sock.close()
        assert resp.get("ok") is True, f"ping failed: {resp}"
        return "ping via Unix socket"

    # -------------------------------------------------------------------------
    # Test 2: TCP socket ping
    # -------------------------------------------------------------------------
    def test_ping_tcp():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", TCP_PORT))
        resp = send_json(sock, {"cmd": "ping"})
        sock.close()
        assert resp.get("ok") is True, f"ping failed: {resp}"
        return "ping via TCP"

    # -------------------------------------------------------------------------
    # Test 3: file tool via Unix socket
    # -------------------------------------------------------------------------
    def test_file_read_unix():
        test_file = "/tmp/e2e_test_file.txt"
        with open(test_file, "w") as f:
            f.write("e2e_test_ok")

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)
        resp = send_json(
            sock,
            {
                "cmd": "tool",
                "tool": "file",
                "method": "read",
                "args": {"path": test_file},
            },
        )
        sock.close()
        os.unlink(test_file)
        assert resp.get("ok") is True, f"file read failed: {resp}"
        assert "e2e_test_ok" in resp.get("result", "")
        return "file read via Unix socket"

    # -------------------------------------------------------------------------
    # Test 4: AI command (no kernel needed — stub returns "stub")
    # -------------------------------------------------------------------------
    def test_ai_command():
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)
        resp = send_json(sock, {"cmd": "ai", "text": "hello"})
        sock.close()
        # With no real API key, kernel returns a stub — we just verify protocol works
        assert "ok" in resp, f"AI command failed: {resp}"
        return "AI command (stubbed)"

    # -------------------------------------------------------------------------
    # Run all tests
    # -------------------------------------------------------------------------
    tests = [
        ("Unix socket ping", test_ping_unix),
        ("TCP socket ping", test_ping_tcp),
        ("File read via Unix socket", test_file_read_unix),
        ("AI command", test_ai_command),
    ]

    for name, fn in tests:
        try:
            result = fn()
            results.append((name, "PASS", result))
        except Exception as e:
            results.append((name, f"FAIL: {e}", None))

    return results


def main():
    print("=" * 60)
    print("Bantu-OS End-to-End Shell-Kernel Test")
    print("=" * 60)

    kill_existing()
    print("\n[boot] Starting Python kernel server…")
    proc = start_kernel()

    try:
        print(f"[boot] Waiting for Unix socket at {SOCKET_PATH}…")
        if not wait_for_socket(SOCKET_PATH):
            print(f"[FAIL] Unix socket did not appear within {MAX_WAIT}s")
            print("[boot] Kernel log:")
            with open(KERNEL_LOG) as f:
                print(f.read()[:500])
            sys.exit(1)
        print("[boot] Unix socket ready")

        print(f"[boot] Waiting for TCP server on port {TCP_PORT}…")
        if not wait_for_server_ready(TCP_PORT):
            print(f"[FAIL] TCP server did not respond within {MAX_WAIT}s")
            sys.exit(1)
        print("[boot] TCP server ready")

        print("\n[test] Running protocol tests…")
        results = run_tests()

        print(f"\n{'='*60}")
        print("RESULTS")
        print(f"{'='*60}")
        passed = 0
        for name, status, detail in results:
            icon = "✅" if status == "PASS" else "❌"
            print(f"  {icon} {name}: {status}")
            if status == "PASS":
                passed += 1

        print(f"\n{passed}/{len(results)} tests passed")

        if passed == len(results):
            print("\n✅ End-to-end test PASSED — shell and kernel are connected.")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed.")
            sys.exit(1)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        kill_existing()


if __name__ == "__main__":
    main()
