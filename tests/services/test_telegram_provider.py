from __future__ import annotations

import aiohttp
import pytest

from bantu_os.services.messaging import MessagingService


class FakeResponse:
    def __init__(self, payload: dict, status: int = 200):
        self.payload = payload
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.requested_url = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    def get(self, url):
        self.requested_url = url
        return self.response


@pytest.mark.asyncio
async def test_telegram_provider_health_checks_get_me(monkeypatch):
    response = FakeResponse({"ok": True, "result": {"id": 42, "username": "bantu_bot"}})
    session = FakeSession(response)
    monkeypatch.setattr(aiohttp, "ClientSession", lambda **_: session)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")

    result = await MessagingService().telegram_provider_health()

    assert result == {
        "provider": "telegram",
        "configured": True,
        "reachable": True,
        "bot_id": 42,
        "bot_username": "bantu_bot",
    }
    assert session.requested_url.endswith("/bottest-token/getMe")


@pytest.mark.asyncio
async def test_telegram_provider_health_rejects_api_failure(monkeypatch):
    response = FakeResponse({"ok": False, "description": "Unauthorized"}, status=401)
    monkeypatch.setattr(aiohttp, "ClientSession", lambda **_: FakeSession(response))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bad-token")

    with pytest.raises(RuntimeError, match="Unauthorized"):
        await MessagingService().telegram_provider_health()


@pytest.mark.asyncio
async def test_telegram_provider_health_requires_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    with pytest.raises(EnvironmentError, match="TELEGRAM_BOT_TOKEN"):
        await MessagingService().telegram_provider_health()
