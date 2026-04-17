"""
Tests for FintechService (Phase 2).
All tool tests are skipped until implementation.
"""
from __future__ import annotations

import pytest
from bantu_os.services.fintech.fintech_service import FintechService


class TestFintechService:
    @pytest.fixture
    def svc(self) -> FintechService:
        return FintechService()

    def test_health_check(self, svc: FintechService) -> None:
        result = svc.health_check()
        assert result["status"] == "ok"
        assert result["service"] == "fintech"

    def test_service_info(self, svc: FintechService) -> None:
        info = svc.get_service_info()
        assert info["name"] == "fintech"

    def test_schema_fields(self, svc: FintechService) -> None:
        schema = svc.tool_schema
        tool_names = list(schema.keys())
        assert tool_names == [
            'fintech_create_payment',
            'fintech_check_balance',
            'fintech_request_mpesa',
            'fintech_request_flutterwave',
            'fintech_request_paystack',
        ]

    @pytest.mark.asyncio
    async def test_create_payment(self, svc: FintechService) -> None:
        pytest.skip("fintech_create_payment not yet implemented")

    @pytest.mark.asyncio
    async def test_request_mpesa(self, svc: FintechService) -> None:
        pytest.skip("fintech_request_mpesa not yet implemented")

    @pytest.mark.asyncio
    async def test_request_flutterwave(self, svc: FintechService) -> None:
        pytest.skip("fintech_request_flutterwave not yet implemented")

    @pytest.mark.asyncio
    async def test_request_paystack(self, svc: FintechService) -> None:
        pytest.skip("fintech_request_paystack not yet implemented")