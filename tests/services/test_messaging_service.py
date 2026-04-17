"""
Tests for MessagingService (Phase 2).
All tool tests are skipped until implementation.
"""
from __future__ import annotations

import pytest
from bantu_os.services.messaging.messaging_service import MessagingService


class TestMessagingService:
    @pytest.fixture
    def svc(self) -> MessagingService:
        return MessagingService()

    def test_health_check(self, svc: MessagingService) -> None:
        result = svc.health_check()
        assert result["status"] == "ok"
        assert result["service"] == "messaging"

    def test_service_info(self, svc: MessagingService) -> None:
        info = svc.get_service_info()
        assert info["name"] == "messaging"

    def test_schema_fields(self, svc: MessagingService) -> None:
        schema = svc.tool_schema
        tool_names = list(schema.keys())
        assert tool_names == [
            'messaging_send_email',
            'messaging_send_sms',
            'messaging_send_telegram',
        ]

    @pytest.mark.asyncio
    async def test_send_email(self, svc: MessagingService) -> None:
        pytest.skip("messaging_send_email not yet implemented")

    @pytest.mark.asyncio
    async def test_send_sms(self, svc: MessagingService) -> None:
        pytest.skip("messaging_send_sms not yet implemented")

    @pytest.mark.asyncio
    async def test_send_telegram(self, svc: MessagingService) -> None:
        pytest.skip("messaging_send_telegram not yet implemented")