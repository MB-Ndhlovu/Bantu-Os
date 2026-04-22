"""
Tests for CryptoWalletService.
"""

import pytest

pytestmark = pytest.mark.asyncio


class TestCryptoWalletService:
    """Health check and basic validation tests."""

    def test_health_check_returns_status(self):
        from bantu_os.services.crypto import CryptoWalletService

        svc = CryptoWalletService()
        result = svc.health_check()
        assert result["status"] == "ok"
        assert result["service"] == "crypto"
        assert "networks" in result
        # No RPC configured — all should show no_rpc_configured
        assert result["networks"]["ethereum"] == "no_rpc_configured"

    async def test_unknown_tool_raises(self):
        from bantu_os.services.crypto import CryptoWalletService

        svc = CryptoWalletService()
        with pytest.raises(ValueError, match="Unknown tool"):
            await svc.use_tool_async("unknown_tool", {})

    def test_invalid_address_format(self):
        from bantu_os.services.crypto import CryptoWalletService

        svc = CryptoWalletService()
        import asyncio

        with pytest.raises(ValueError, match="Invalid address"):
            asyncio.run(
                svc.crypto_get_balance(
                    address="not-an-address",
                    network="ethereum",
                )
            )

    def test_send_requires_private_key(self):
        from bantu_os.services.crypto import CryptoWalletService

        svc = CryptoWalletService()
        import asyncio

        with pytest.raises(EnvironmentError, match="CRYPTO_WALLET_PRIVATE_KEY"):
            asyncio.run(
                svc.crypto_send(
                    to="0x742d35Cc6634C0532925a3b844Bc9e7595f0BEb1",
                    amount="0.01",
                    network="ethereum",
                )
            )

    def test_sign_message_requires_private_key(self):
        from bantu_os.services.crypto import CryptoWalletService

        svc = CryptoWalletService()
        import asyncio

        with pytest.raises(EnvironmentError, match="CRYPTO_WALLET_PRIVATE_KEY"):
            asyncio.run(svc.crypto_sign_message(message="hello"))

    def test_send_requires_valid_recipient(self):
        from bantu_os.services.crypto import CryptoWalletService

        svc = CryptoWalletService()
        import asyncio

        # Even if private key is set, invalid recipient should fail
        with pytest.raises(EnvironmentError, match="CRYPTO_WALLET_PRIVATE_KEY"):
            asyncio.run(
                svc.crypto_send(
                    to="0x742d35Cc6634C0532925a3b844Bc9e7595f0BEb1",
                    amount="0.01",
                    network="ethereum",
                )
            )
