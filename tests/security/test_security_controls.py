from __future__ import annotations

import asyncio
import json
import stat
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer

from bantu_os.api.api_key_store import APIKeyStore
from bantu_os.api.server import create_app
from bantu_os.core.socket_server import SocketServer


@pytest.mark.asyncio
async def test_unix_socket_is_owner_only(tmp_path: Path) -> None:
    socket_path = tmp_path / "bantu.sock"
    server = SocketServer(unix_path=str(socket_path), tcp_port=0)
    task = asyncio.create_task(server.run())
    try:
        for _ in range(50):
            if socket_path.exists():
                break
            await asyncio.sleep(0.01)
        else:
            pytest.fail("Unix socket was not created")
        assert stat.S_IMODE(socket_path.stat().st_mode) == 0o600
    finally:
        await server.shutdown()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_api_key_store_writes_private_atomic_file(tmp_path: Path) -> None:
    path = tmp_path / "api_keys.json"
    store = APIKeyStore(path)
    key, _ = await store.create_key()
    assert await store.verify(key)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert not path.with_suffix(".json.tmp").exists()
    assert json.loads(path.read_text())


@pytest.mark.asyncio
async def test_api_key_creation_requires_admin_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BANTU_ADMIN_API_KEY", "admin-test-key")
    store = APIKeyStore(tmp_path / "api_keys.json")
    client = TestClient(TestServer(create_app(api_key_store=store)))
    await client.start_server()
    try:
        response = await client.post("/api/auth/key", json={"label": "test"})
        assert response.status == 401

        response = await client.post(
            "/api/auth/key",
            json={"label": "test"},
            headers={"Authorization": "Bearer admin-test-key"},
        )
        assert response.status == 201
        payload = await response.json()
        assert payload["api_key"].startswith("bnta_")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_password_hashing_uses_salted_kdf() -> None:
    from bantu_os.auth.password import hash_password, verify_password

    digest, salt = hash_password("secret")
    assert len(digest) == 64
    assert len(salt) == 32
    assert verify_password("secret", digest, salt)
    assert not verify_password("wrong", digest, salt)
