"""
Tests for CryptoWalletService (Phase 2).
All tool tests are skipped until implementation.
"""
from __future__ import annotations

import pytest
from bantu_os.services.crypto.crypto_service import CryptoWalletService


class TestCryptoWalletService:
    @pytest.fixture
    def svc(self) -> CryptoWalletService:
        return CryptoWalletService()

    def test_health_check(self, svc: CryptoWalletService) -> None:
        result = svc.health_check()
        assert result["status"] == "ok"
        assert result["service"] == "crypto"

    def test_service_info(self, svc: CryptoWalletService) -> None:
        info = svc.get_service_info()
        assert info["name"] == "crypto"

    def test_supported_networks(self, svc: CryptoWalletService) -> None:
        assert "ethereum" in svc.SUPPORTED_NETWORKS
        assert "polygon" in svc.SUPPORTED_NETWORKS
        assert "base" in svc.SUPPORTED_NETWORKS
        assert "bsc" in svc.SUPPORTED_NETWORKS

    @pytest.mark.asyncio
    async def test_get_balance(self, svc: CryptoWalletService) -> None:
        pytest.skip("crypto_get_balance not yet implemented")

    @pytest.mark.asyncio
    async def test_send(self, svc: CryptoWalletService) -> None:
        pytest.skip("crypto_send not yet implemented")

    @pytest.mark.asyncio
    async def test_sign_message(self, svc: CryptoWalletService) -> None:
        pytest.skip("crypto_sign_message not yet implemented")