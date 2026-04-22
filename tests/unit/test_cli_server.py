"""
Tests for cli/server.py — CLIServer
"""

import json
import socket

import pytest

from bantu_os.cli.server import CLIServer


@pytest.fixture
def server(tmp_path):
    sock_path = str(tmp_path / "bantu.sock")
    srv = CLIServer(socket_path=sock_path)
    srv.setup()
    yield srv
    srv.stop()


def test_server_ping(server):
    server.start(background=False)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(server.socket_path)
    sock.sendall(json.dumps({"cmd": "ping"}).encode())
    resp = json.loads(sock.recv(4096).decode())
    sock.close()
    assert resp["ok"] is True
    assert resp["pong"] is True


def test_server_status(server):
    server.start(background=False)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(server.socket_path)
    sock.sendall(json.dumps({"cmd": "status"}).encode())
    resp = json.loads(sock.recv(4096).decode())
    sock.close()
    assert resp["ok"] is True
    assert resp["status"] == "running"
    sock.close()


def test_server_unknown_command(server):
    server.start(background=False)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(server.socket_path)
    sock.sendall(json.dumps({"cmd": "unknown"}).encode())
    resp = json.loads(sock.recv(4096).decode())
    sock.close()
    assert resp["ok"] is False
    assert "Unknown command" in resp["error"]
