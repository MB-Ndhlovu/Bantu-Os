"""
CryptoWalletService tool schemas.
EVM-compatible wallet operations.

Env vars required:
  ETHEREUM_RPC_URL              — RPC endpoint URL (Infura/Alchemy/etc.)
  CRYPTO_WALLET_PRIVATE_KEY     — Wallet private key (encrypted at rest via secrets.py)
  CRYPTO_WALLET_ADDRESS        — Default wallet address (EOA)
"""
from __future__ import annotations

TOOL_SCHEMAS = {
    "crypto_get_balance": {
        "description": (
            "Query the balance of a wallet address on a given EVM network. "
            "Returns native currency balance and, if a token address is provided, "
            "the ERC-20 token balance."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": (
                        "The wallet address (0x...). "
                        "Defaults to CRYPTO_WALLET_ADDRESS if not provided."
                    ),
                    "nullable": True,
                },
                "network": {
                    "type": "string",
                    "description": "EVM network name.",
                    "enum": ["ethereum", "polygon", "base", "bsc"],
                    "default": "ethereum",
                },
                "token": {
                    "type": "string",
                    "description": (
                        "Token contract address. "
                        "If omitted, returns the native currency balance."
                    ),
                    "nullable": True,
                },
            },
            "required": [],
        },
        "returns": {
            "type": "object",
            "properties": {
                "balance": {
                    "type": "string",
                    "description": "Balance in the smallest unit (wei for ETH, satoshi for MATIC, etc.).",
                },
                "balance_human": {
                    "type": "string",
                    "description": "Balance in human-readable units.",
                },
                "symbol": {
                    "type": "string",
                    "description": "Token symbol (e.g. 'ETH', 'MATIC').",
                },
                "decimals": {
                    "type": "integer",
                    "description": "Token decimals used for unit conversion.",
                },
            },
        },
    },
    "crypto_send": {
        "description": (
            "Send native currency or an ERC-20 token to another address. "
            "Estimates gas before sending and prompts the user for confirmation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient wallet address (0x...).",
                },
                "amount": {
                    "type": "string",
                    "description": (
                        "Amount to send in the smallest unit (wei for ETH). "
                        "Use crypto_get_balance to verify sufficient balance first."
                    ),
                },
                "network": {
                    "type": "string",
                    "description": "EVM network.",
                    "enum": ["ethereum", "polygon", "base", "bsc"],
                    "default": "ethereum",
                },
                "token": {
                    "type": "string",
                    "description": (
                        "Token contract address. "
                        "If omitted, sends the native currency."
                    ),
                    "nullable": True,
                },
            },
            "required": ["to", "amount"],
        },
        "returns": {
            "type": "object",
            "properties": {
                "tx_hash": {
                    "type": "string",
                    "description": "Ethereum transaction hash (0x...).",
                },
                "status": {
                    "type": "string",
                    "description": "'submitted', 'confirmed', or 'failed'.",
                },
            },
        },
    },
    "crypto_sign_message": {
        "description": (
            "Sign an arbitrary message using the wallet's private key. "
            "Used for off-chain authentication challenges."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The raw message string to sign.",
                },
                "address": {
                    "type": "string",
                    "description": (
                        "Wallet address to sign with. "
                        "Defaults to CRYPTO_WALLET_ADDRESS if not provided."
                    ),
                    "nullable": True,
                },
            },
            "required": ["message"],
        },
        "returns": {
            "type": "object",
            "properties": {
                "signature": {
                    "type": "string",
                    "description": "Ethereum signed message signature (0x...).",
                },
                "address": {
                    "type": "string",
                    "description": "Address that produced the signature.",
                },
            },
        },
    },
}