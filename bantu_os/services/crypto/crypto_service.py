"""
CryptoWalletService — Phase 2 skeleton.
EVM-compatible wallet operations: balance, send, sign.

TOOLS (not yet implemented):
  - crypto_get_balance
  - crypto_send
  - crypto_sign_message
"""
from __future__ import annotations

import pytest
from typing import Any, Dict, Optional
from bantu_os.services.service_base import ServiceBase


class CryptoWalletService(ServiceBase):
    """EVM wallet service for balance queries and transactions."""

    SUPPORTED_NETWORKS = ["ethereum", "polygon", "base", "bsc"]

    def __init__(self) -> None:
        super().__init__(name="crypto")
        self._web3: Optional[Any] = None

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "service": self.name}

    @property
    def tool_schema(self) -> Dict[str, Any]:
        return {
            "crypto_get_balance": {
                "description": "Get the balance of a crypto wallet.",
                "parameters": {
                    "address": {"type": "string", "description": "The wallet address."},
                    "network": {
                        "type": "string",
                        "description": "The network to query.",
                        "enum": self.SUPPORTED_NETWORKS,
                    },
                    "token": {
                        "type": "string",
                        "description": "The token to query. If not specified, the native currency is used.",
                        "nullable": True,
                    },
                },
                "returns": {
                    "type": "object",
                    "properties": {
                        "balance": {"type": "string", "description": "The balance in wei."},
                        "symbol": {"type": "string", "description": "The token symbol."},
                        "decimals": {"type": "integer", "description": "The number of decimals."},
                    },
                },
            },
            "crypto_send": {
                "description": "Send crypto to another address.",
                "parameters": {
                    "to": {"type": "string", "description": "The recipient address."},
                    "amount": {"type": "string", "description": "The amount to send in wei."},
                    "network": {
                        "type": "string",
                        "description": "The network to send on.",
                        "enum": self.SUPPORTED_NETWORKS,
                    },
                    "token": {
                        "type": "string",
                        "description": "The token to send. If not specified, the native currency is used.",
                        "nullable": True,
                    },
                },
                "returns": {
                    "type": "object",
                    "properties": {
                        "tx_hash": {"type": "string", "description": "The transaction hash."},
                    },
                },
            },
            "crypto_sign_message": {
                "description": "Sign a message with a private key.",
                "parameters": {
                    "message": {"type": "string", "description": "The message to sign."},
                    "address": {
                        "type": "string",
                        "description": "The address to sign with. If not specified, the default address is used.",
                        "nullable": True,
                    },
                },
                "returns": {
                    "type": "object",
                    "properties": {
                        "signature": {"type": "string", "description": "The signature."},
                    },
                },
            },
        }

    # ─── Tool stubs (implement in next phase) ────────────────────

    async def crypto_get_balance(
        self,
        address: Optional[str] = None,
        network: str = "ethereum",
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        pytest.skip("crypto_get_balance not yet implemented")

    async def crypto_send(
        self,
        to: str,
        amount: str,
        network: str = "ethereum",
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        pytest.skip("crypto_send not yet implemented")

    async def crypto_sign_message(
        self,
        message: str,
        address: Optional[str] = None,
    ) -> Dict[str, Any]:
        pytest.skip("crypto_sign_message not yet implemented")