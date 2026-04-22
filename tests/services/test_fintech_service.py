"""
Tests for FintechService.
"""

import pytest

pytestmark = pytest.mark.asyncio


class TestFintechService:
    """Health check and schema tests."""

    def test_health_check_returns_status(self):
        from bantu_os.services.fintech import FintechService

        svc = FintechService()
        result = svc.health_check()
        assert result["status"] == "ok"
        assert result["service"] == "fintech"
        assert "stripe_configured" in result
        assert "mpesa_configured" in result
        assert "flutterwave_configured" in result
        assert "paystack_configured" in result

    async def test_unknown_tool_raises(self):
        from bantu_os.services.fintech import FintechService

        svc = FintechService()
        with pytest.raises(ValueError, match="Unknown tool"):
            await svc.use_tool_async("unknown_tool", {})

    async def test_create_payment_requires_stripe_key(self):
        from bantu_os.services.fintech import FintechService

        svc = FintechService()
        with pytest.raises(EnvironmentError, match="STRIPE_SECRET_KEY"):
            await svc.fintech_create_payment(
                amount=100,
                currency="usd",
                customer_email="test@example.com",
            )

    async def test_check_balance_unknown_provider(self):
        from bantu_os.services.fintech import FintechService

        svc = FintechService()
        with pytest.raises(ValueError, match="Unknown provider"):
            await svc.fintech_check_balance(provider="unknown")

    async def test_mpesa_requires_credentials(self):
        from bantu_os.services.fintech import FintechService

        svc = FintechService()
        with pytest.raises(EnvironmentError, match="MPESA_CONSUMER_KEY"):
            await svc.fintech_request_mpesa(
                phone="+254712345678",
                amount=100,
                reference="TEST-001",
            )

    async def test_paystack_requires_key(self):
        from bantu_os.services.fintech import FintechService

        svc = FintechService()
        with pytest.raises(EnvironmentError, match="PAYSTACK_SECRET_KEY"):
            await svc.fintech_request_paystack(
                amount=5000,
                email="test@example.com",
            )

    async def test_flutterwave_requires_key(self):
        from bantu_os.services.fintech import FintechService

        svc = FintechService()
        with pytest.raises(EnvironmentError, match="FLUTTERWAVE_SECRET_KEY"):
            await svc.fintech_request_flutterwave(
                amount=100,
                currency="ZAR",
                reference="TEST-001",
            )
