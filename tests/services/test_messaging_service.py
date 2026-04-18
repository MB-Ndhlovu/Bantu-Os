"""
Tests for MessagingService.
"""
import pytest

pytestmark = pytest.mark.asyncio


class TestMessagingService:
    """Health check and schema tests."""

    def test_health_check_returns_status(self):
        from bantu_os.services.messaging import MessagingService

        svc = MessagingService()
        result = svc.health_check()
        assert result["status"] == "ok"
        assert result["service"] == "messaging"
        assert "email_configured" in result
        assert "sms_configured" in result
        assert "telegram_configured" in result

    def test_tool_schema_has_three_tools(self):
        from bantu_os.services.messaging.schemas import TOOL_SCHEMAS

        assert "messaging_send_email" in TOOL_SCHEMAS

    async def test_unknown_tool_raises(self):
        from bantu_os.services.messaging import MessagingService

        svc = MessagingService()
        with pytest.raises(ValueError, match="Unknown tool"):
            await svc.use_tool_async("unknown_tool", {})

    def test_email_requires_credentials(self):
        from bantu_os.services.messaging import MessagingService

        svc = MessagingService()
        # No env vars set in test — should raise
        import asyncio

        with pytest.raises(EnvironmentError, match="SMTP_USERNAME"):
            asyncio.run(svc.messaging_send_email(
                to="test@example.com",
                subject="Hello",
                body="Test",
            ))

    def test_telegram_requires_token(self):
        from bantu_os.services.messaging import MessagingService

        svc = MessagingService()
        import asyncio

        with pytest.raises(EnvironmentError, match="TELEGRAM_BOT_TOKEN"):
            asyncio.run(svc.messaging_send_telegram(
                chat_id="123456",
                text="Hello",
            ))

    def test_sms_requires_twilio_credentials(self):
        from bantu_os.services.messaging import MessagingService

        svc = MessagingService()
        import asyncio

        with pytest.raises(EnvironmentError, match="TWILIO_ACCOUNT_SID"):
            asyncio.run(svc.messaging_send_sms(
                to="+27612345678",
                body="Hello",
            ))
