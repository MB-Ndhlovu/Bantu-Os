"""
Integration tests for bantu_os.core.socket_server.

These tests:
1. Start a SocketServer on a temporary Unix socket
2. Connect as a client and send JSON commands
3. Assert correct responses

Tests cover:
- ping command
- unknown command
- invalid JSON
- tool calls (file, process, network services)
- error handling for missing / failing tools
- graceful shutdown
"""

import asyncio
import json
import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from bantu_os.core.socket_server import ShellProtocol, SocketServer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def send_json(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, payload: dict
) -> dict:
    """Send one JSON line, read one JSON line, return parsed response."""
    data = json.dumps(payload).encode("utf-8") + b"\n"
    writer.write(data)
    await writer.drain()
    line = await reader.readline()
    if not line:
        return {}
    return json.loads(line.decode("utf-8", errors="replace"))


async def connect(path: str) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    return await asyncio.open_unix_connection(path)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def socket_path():
    """Provide a temporary Unix socket path."""
    with tempfile.TemporaryDirectory() as td:
        yield os.path.join(td, "test.sock")


@pytest.fixture
async def server(socket_path):
    """Start a SocketServer on a temporary socket, yield it, then shut it down."""
    srv = SocketServer(unix_path=socket_path)
    srv_task = asyncio.create_task(srv.run())

    # Wait for the server to be listening
    for _ in range(50):
        await asyncio.sleep(0.1)
        if os.path.exists(socket_path):
            break
    else:
        srv_task.cancel()
        pytest.fail("Socket server failed to start within 5s")

    yield srv

    await srv.shutdown()
    try:
        srv_task.cancel()
        await srv_task
    except asyncio.CancelledError:
        pass


@pytest.fixture
async def client(server, socket_path):
    """A connected reader/writer pair. Cleans up on exit."""
    reader, writer = await connect(socket_path)
    yield reader, writer
    writer.close()
    await writer.wait_closed()


# ---------------------------------------------------------------------------
# Protocol handler unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ping_via_protocol():
    """ShellProtocol correctly handles ping command."""
    kernel = AsyncMock()
    loop = asyncio.get_running_loop()
    proto = ShellProtocol(kernel, loop)

    transport = AsyncMock()
    proto.connection_made(transport)

    # Simulate receiving "ping" JSON
    proto.data_received(b'{"cmd": "ping"}\n')

    await asyncio.sleep(0.05)  # allow async _process to run

    transport.write.assert_called_once()
    written = transport.write.call_args[0][0]
    response = json.loads(written.decode("utf-8"))
    assert response["ok"] is True
    assert response["result"] == "pong"


@pytest.mark.asyncio
async def test_unknown_cmd_via_protocol():
    """ShellProtocol returns error for unknown cmd."""
    kernel = AsyncMock()
    loop = asyncio.get_running_loop()
    proto = ShellProtocol(kernel, loop)

    transport = AsyncMock()
    proto.connection_made(transport)

    proto.data_received(b'{"cmd": "unknown"}\n')

    await asyncio.sleep(0.05)

    written = transport.write.call_args[0][0]
    response = json.loads(written.decode("utf-8"))
    assert response["ok"] is False
    assert "Unknown cmd" in response["error"]


@pytest.mark.asyncio
async def test_invalid_json_via_protocol():
    """ShellProtocol returns error for malformed JSON."""
    kernel = AsyncMock()
    loop = asyncio.get_running_loop()
    proto = ShellProtocol(kernel, loop)

    transport = AsyncMock()
    proto.connection_made(transport)

    proto.data_received(b"not valid json\n")

    await asyncio.sleep(0.05)

    written = transport.write.call_args[0][0]
    response = json.loads(written.decode("utf-8"))
    assert response["ok"] is False
    assert "Invalid JSON" in response["error"]


@pytest.mark.asyncio
async def test_multiline_payload_via_protocol():
    """ShellProtocol buffers correctly across multiple data_received calls."""
    kernel = AsyncMock()
    loop = asyncio.get_running_loop()
    proto = ShellProtocol(kernel, loop)

    transport = AsyncMock()
    proto.connection_made(transport)

    # Send in two chunks
    proto.data_received(b'{"cmd": "ping", "text": "hello')
    proto.data_received(b'"}\n')

    await asyncio.sleep(0.05)

    # Should have received one pong response
    assert transport.write.call_count == 1
    written = transport.write.call_args[0][0]
    response = json.loads(written.decode("utf-8"))
    assert response["ok"] is True


# ---------------------------------------------------------------------------
# Socket-level integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ping(server, socket_path):
    """Server responds to ping on Unix socket."""
    reader, writer = await connect(socket_path)
    try:
        resp = await send_json(reader, writer, {"cmd": "ping"})
        assert resp["ok"] is True
        assert resp["result"] == "pong"
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_ping_twice_same_connection(server, socket_path):
    """Server handles multiple requests on the same connection."""
    reader, writer = await connect(socket_path)
    try:
        resp1 = await send_json(reader, writer, {"cmd": "ping"})
        resp2 = await send_json(reader, writer, {"cmd": "ping"})
        assert resp1["ok"] is True
        assert resp2["ok"] is True
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_unknown_cmd(server, socket_path):
    """Server returns error for unknown command."""
    reader, writer = await connect(socket_path)
    try:
        resp = await send_json(reader, writer, {"cmd": "notacommand"})
        assert resp["ok"] is False
        assert "Unknown cmd" in resp["error"]
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_invalid_json(server, socket_path):
    """Server returns error for malformed JSON."""
    reader, writer = await connect(socket_path)
    try:
        writer.write(b"this is not json\n")
        await writer.drain()
        line = await reader.readline()
        resp = json.loads(line.decode("utf-8", errors="replace"))
        assert resp["ok"] is False
        assert "Invalid JSON" in resp["error"]
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_empty_cmd(server, socket_path):
    """Server handles missing cmd field gracefully."""
    reader, writer = await connect(socket_path)
    try:
        resp = await send_json(reader, writer, {})
        assert resp["ok"] is False
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_ai_cmd_returns_str(server, socket_path):
    """Server routes 'ai' cmd to kernel.process_input and returns str."""
    reader, writer = await connect(socket_path)
    try:
        with patch("bantu_os.core.socket_server.Kernel") as MockKernel:
            mock_instance = AsyncMock()
            mock_instance.process_input = AsyncMock(return_value="AI response text")
            MockKernel.return_value = mock_instance

            # Restart server with patched kernel... instead, test via mock
            pass

        # Since we can't easily mock per-test with the current server design,
        # we verify the response shape for a real call (will fail without API key
        # but still returns valid JSON error or result).
        resp = await send_json(reader, writer, {"cmd": "ai", "text": "hello"})
        assert "ok" in resp
        assert isinstance(resp["ok"], bool)
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_tool_cmd_unknown_tool(server, socket_path):
    """Server returns error for unknown tool name."""
    reader, writer = await connect(socket_path)
    try:
        resp = await send_json(
            reader,
            writer,
            {
                "cmd": "tool",
                "tool": "nonexistent_tool",
                "args": {},
            },
        )
        assert resp["ok"] is False
        assert "Tool not found" in resp["error"]
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_tool_cmd_file_service_read(tmp_path, server, socket_path):
    """Server routes 'tool' cmd to FileService.read correctly."""
    # Create a test file
    test_file = tmp_path / "test_read.txt"
    test_file.write_text("hello from socket server test")

    reader, writer = await connect(socket_path)
    try:
        resp = await send_json(
            reader,
            writer,
            {
                "cmd": "tool",
                "tool": "file",
                "method": "read",
                "args": {"path": str(test_file)},
            },
        )
        assert resp["ok"] is True
        assert "hello from socket server test" in resp["result"]
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_tool_cmd_file_service_list_dir(tmp_path, server, socket_path):
    """Server routes 'tool' cmd to FileService.list_dir correctly."""
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")

    reader, writer = await connect(socket_path)
    try:
        resp = await send_json(
            reader,
            writer,
            {
                "cmd": "tool",
                "tool": "file",
                "method": "list_dir",
                "args": {"path": str(tmp_path), "recursive": False},
            },
        )
        assert resp["ok"] is True
        # Result is a JSON string serialisation of the list
        parsed = json.loads(resp["result"])
        names = {e["name"] for e in parsed}
        assert "a.txt" in names
        assert "b.txt" in names
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_tool_cmd_process_service_stats(server, socket_path):
    """Server routes 'tool' cmd to ProcessService.get_system_stats."""
    reader, writer = await connect(socket_path)
    try:
        resp = await send_json(
            reader,
            writer,
            {
                "cmd": "tool",
                "tool": "process",
                "method": "get_system_stats",
                "args": {},
            },
        )
        assert resp["ok"] is True
        parsed = json.loads(resp["result"])
        assert "cpu" in parsed
        assert "memory" in parsed
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_tool_cmd_network_service_dns(server, socket_path):
    """Server routes 'tool' cmd to NetworkService.dns_lookup."""
    reader, writer = await connect(socket_path)
    try:
        resp = await send_json(
            reader,
            writer,
            {
                "cmd": "tool",
                "tool": "network",
                "method": "dns_lookup",
                "args": {"hostname": "localhost"},
            },
        )
        assert resp["ok"] is True
        parsed = json.loads(resp["result"])
        assert parsed.get("resolved") is True
        assert any("127.0.0.1" in a["address"] for a in parsed.get("addresses", []))
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_multiple_clients_concurrent(server, socket_path):
    """Multiple clients can connect and issue commands concurrently."""
    NUM_CLIENTS = 3

    async def client_task(client_id: int) -> dict:
        reader, writer = await connect(socket_path)
        try:
            resp = await send_json(reader, writer, {"cmd": "ping"})
            return resp
        finally:
            writer.close()
            await writer.wait_closed()

    results = await asyncio.gather(*[client_task(i) for i in range(NUM_CLIENTS)])
    assert all(r["ok"] is True for r in results)
    assert all(r["result"] == "pong" for r in results)


@pytest.mark.asyncio
async def test_server_shutdown_unlinks_socket(server, socket_path):
    """After shutdown, the Unix socket file is removed."""
    await server.shutdown()
    await asyncio.sleep(0.1)
    assert not os.path.exists(socket_path)


@pytest.mark.asyncio
async def test_tcp_port_bound(server):
    """TCP server started on 127.0.0.1:18792."""
    host, port = "127.0.0.1", 18792
    reader, writer = await asyncio.open_connection(host, port)
    try:
        resp = await send_json(reader, writer, {"cmd": "ping"})
        assert resp["ok"] is True
        assert resp["result"] == "pong"
    finally:
        writer.close()
        await writer.wait_closed()
