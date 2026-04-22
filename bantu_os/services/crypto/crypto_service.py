"""
CryptoWalletService — Phase 2.

EVM-compatible wallet service: balance queries, token transfers, message signing.
Supports Ethereum, Polygon, Base, and Binance Smart Chain.

Exposes three tools to the Bantu-OS kernel via ``use_tool_async``:

    crypto_get_balance   — query wallet balance (native or ERC-20)
    crypto_send          — transfer native tokens or ERC-20 tokens
    crypto_sign_message  — sign an arbitrary message with the wallet key

Env vars required:
    ETHEREUM_RPC_URL             RPC endpoint URL (Infura / Alchemy / etc.)
    CRYPTO_WALLET_PRIVATE_KEY    Wallet private key (0x...)
    CRYPTO_WALLET_ADDRESS       Default wallet address (EOA)

Supported networks:
    ethereum  — Ethereum Mainnet (chain-id: 1)
    polygon   — Polygon PoS (chain-id: 137)
    base      — Base (chain-id: 8453)
    bsc       — Binance Smart Chain (chain-id: 56)
"""

from __future__ import annotations

import os
from typing import Any

from web3 import AsyncWeb3


class CryptoWalletService:
    """
    EVM wallet service for balance queries, token transfers, and message signing.

    Supported networks: Ethereum, Polygon, Base, Binance Smart Chain.
    """

    # Chain ID → RPC URL env var
    RPC_CHAIN_IDS: dict[int, str] = {
        1: "ETHEREUM_RPC_URL",
        137: "POLYGON_RPC_URL",
        8453: "BASE_RPC_URL",
        56: "BSC_RPC_URL",
    }

    # Chain name → chain ID
    NETWORK_CHAIN_IDS: dict[str, int] = {
        "ethereum": 1,
        "polygon": 137,
        "base": 8453,
        "bsc": 56,
    }

    def __init__(self) -> None:
        self._private_key = os.getenv("CRYPTO_WALLET_PRIVATE_KEY", "")
        self._default_address = os.getenv("CRYPTO_WALLET_ADDRESS", "")
        self._rpc_url = os.getenv("ETHEREUM_RPC_URL", "")
        # Per-chain RPC overrides
        self._chain_rpcs: dict[int, str] = {
            chain_id: os.getenv(env_var, "")
            for chain_id, env_var in self.RPC_CHAIN_IDS.items()
        }

    def _get_rpc(self, network: str) -> str:
        chain_id = self.NETWORK_CHAIN_IDS.get(network.lower())
        if chain_id and chain_id in self._chain_rpcs and self._chain_rpcs[chain_id]:
            return self._chain_rpcs[chain_id]
        if self._rpc_url:
            return self._rpc_url
        raise EnvironmentError(
            f"No RPC URL configured for network '{network}'. "
            f"Set ETHEREUM_RPC_URL or one of "
            f"{list(self._chain_rpcs.values())}."
        )

    def _get_w3(self, network: str) -> AsyncWeb3:
        rpc = self._get_rpc(network)
        w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc))
        if not w3.is_connected:
            raise ConnectionError(f"Cannot connect to RPC for {network}: {rpc}")
        return w3

    def health_check(self) -> dict[str, Any]:
        results: dict[str, Any] = {"status": "ok", "service": "crypto", "networks": {}}
        for network, chain_id in self.NETWORK_CHAIN_IDS.items():
            # Check per-chain override first, then fallback to default
            rpc = self._chain_rpcs.get(chain_id) or self._rpc_url
            if not rpc:
                results["networks"][network] = "no_rpc_configured"
                continue
            try:
                w3 = self._get_w3(network)
                # sync check for health (is_connected is sync)
                results["networks"][network] = (
                    "ok" if w3.is_connected else "disconnected"
                )
            except Exception as e:
                results["networks"][network] = f"error: {e}"
        return results

    # -------------------------------------------------------------------------
    # Tool dispatcher
    # -------------------------------------------------------------------------

    async def use_tool_async(
        self, tool_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Dispatch a named tool to its implementation method."""
        dispatch: dict[str, Any] = {
            "crypto_get_balance": self.crypto_get_balance,
            "crypto_send": self.crypto_send,
            "crypto_sign_message": self.crypto_sign_message,
        }
        if tool_name not in dispatch:
            raise ValueError(f"[CryptoWalletService] Unknown tool: {tool_name!r}")
        return await dispatch[tool_name](**params)

    # -------------------------------------------------------------------------
    # Balance
    # -------------------------------------------------------------------------

    async def crypto_get_balance(
        self,
        address: str | None = None,
        network: str = "ethereum",
        token: str | None = None,
    ) -> dict[str, Any]:
        """
        Query the balance of a wallet address on an EVM network.

        Parameters
        ----------
        address : str, optional
            Wallet address (0x...).  Defaults to ``CRYPTO_WALLET_ADDRESS``.
        network : str
            EVM network name.  Defaults to ``'ethereum'``.
        token : str, optional
            ERC-20 token contract address.  If omitted, returns native
            currency balance.

        Returns
        -------
        dict
            ``{'balance': '<wei>', 'balance_human': '<eth>', 'symbol': '<SYM>', 'decimals': <n>}``.
        """
        address = (address or self._default_address).lower()
        if not address:
            raise ValueError("No address provided and CRYPTO_WALLET_ADDRESS not set.")
        if not self._is_checksum_address(address):
            raise ValueError(f"Invalid address format: {address}")

        w3 = self._get_w3(network)

        if token:
            # ERC-20 balance
            token_addr = w3.to_checksum_address(token)
            erc20_abi = [
                {
                    "inputs": [
                        {"name": "account", "type": "address"},
                    ],
                    "name": "balanceOf",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function",
                },
                {
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "stateMutability": "view",
                    "type": "function",
                },
                {
                    "inputs": [],
                    "name": "symbol",
                    "outputs": [{"name": "", "type": "string"}],
                    "stateMutability": "view",
                    "type": "function",
                },
            ]
            token_contract = w3.eth.contract(address=token_addr, abi=erc20_abi)
            balance_wei: int = await token_contract.functions.balanceOf(address).call()
            decimals: int = await token_contract.functions.decimals().call()
            symbol: str = await token_contract.functions.symbol().call()
            balance_human = balance_wei / (10**decimals)
        else:
            # Native balance
            balance_wei = await w3.eth.get_balance(address)
            chain_id = self.NETWORK_CHAIN_IDS.get(network.lower(), 1)
            symbol = {1: "ETH", 137: "MATIC", 8453: "ETH", 56: "BNB"}.get(
                chain_id, "ETH"
            )
            decimals = 18
            balance_human = w3.from_wei(balance_wei, "ether")

        return {
            "balance": str(balance_wei),
            "balance_human": str(balance_human),
            "symbol": symbol,
            "decimals": decimals,
            "address": address,
            "network": network,
        }

    # -------------------------------------------------------------------------
    # Send
    # -------------------------------------------------------------------------

    async def crypto_send(
        self,
        to: str,
        amount: str,
        network: str = "ethereum",
        token: str | None = None,
    ) -> dict[str, Any]:
        """
        Send native currency or an ERC-20 token to another address.

        IMPORTANT: The kernel must confirm the transaction with the user
        before executing this tool, as crypto transfers are irreversible.

        Parameters
        ----------
        to : str
            Recipient wallet address (0x...).
        amount : str
            Amount as a decimal string in human-readable units
            (e.g. "0.01" for ETH, "100" for USDC).
        network : str
            EVM network name.  Defaults to ``'ethereum'``.
        token : str, optional
            ERC-20 contract address.  If omitted, sends native currency.

        Returns
        -------
        dict
            ``{'tx_hash': '0x...', 'status': 'submitted', 'network': '<net>'}``.
        """
        if not self._private_key:
            raise EnvironmentError("CRYPTO_WALLET_PRIVATE_KEY not set.")
        if not self._default_address:
            raise ValueError("CRYPTO_WALLET_ADDRESS not set.")

        to_checksum = self._is_checksum_address(to)
        if not to_checksum:
            raise ValueError(f"Invalid recipient address: {to}")

        w3 = self._get_w3(network)
        from_addr = w3.to_checksum_address(self._default_address)
        to_addr = w3.to_checksum_address(to)

        if token:
            # ERC-20 transfer
            token_addr = w3.to_checksum_address(token)
            erc20_abi = [
                {
                    "inputs": [
                        {"name": "to", "type": "address"},
                        {"name": "amount", "type": "uint256"},
                    ],
                    "name": "transfer",
                    "outputs": [{"name": "", "type": "bool"}],
                    "stateMutability": "nonpayable",
                    "type": "function",
                },
                {
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "stateMutability": "view",
                    "type": "function",
                },
            ]
            token_contract = w3.eth.contract(address=token_addr, abi=erc20_abi)
            decimals: int = await token_contract.functions.decimals().call()
            amount_wei = int(float(amount) * (10**decimals))

            nonce = await w3.eth.get_transaction_count(from_addr)
            txn = token_contract.functions.transfer(
                to_addr, amount_wei
            ).build_transaction(
                {
                    "from": from_addr,
                    "nonce": nonce,
                    "gas": 75000,
                    "gasPrice": await w3.eth.gas_price(),
                }
            )
        else:
            # Native ETH transfer
            amount_wei = w3.to_wei(amount, "ether")
            nonce = await w3.eth.get_transaction_count(from_addr)
            txn = {
                "to": to_addr,
                "value": amount_wei,
                "nonce": nonce,
                "gas": 21000,
                "gasPrice": await w3.eth.gas_price(),
                "chainId": self.NETWORK_CHAIN_IDS.get(network.lower(), 1),
            }

        # Sign and send
        signed = w3.eth.account.sign_transaction(txn, self._private_key)
        tx_hash = await w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = await w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        return {
            "tx_hash": tx_hash.hex(),
            "status": "confirmed" if receipt.status == 1 else "failed",
            "network": network,
            "block_number": receipt.blockNumber,
        }

    # -------------------------------------------------------------------------
    # Sign message
    # -------------------------------------------------------------------------

    async def crypto_sign_message(
        self,
        message: str,
        address: str | None = None,
    ) -> dict[str, Any]:
        """
        Sign an arbitrary message using the wallet's private key.

        Used for off-chain authentication challenges (e.g. SIWE / web3 auth).

        Parameters
        ----------
        message : str
            Raw message string to sign.
        address : str, optional
            Wallet address to sign with.  Defaults to ``CRYPTO_WALLET_ADDRESS``.

        Returns
        -------
        dict
            ``{'signature': '0x...', 'address': '0x...'}``.
        """
        if not self._private_key:
            raise EnvironmentError("CRYPTO_WALLET_PRIVATE_KEY not set.")

        address = address or self._default_address
        if not address:
            raise ValueError("No address provided and CRYPTO_WALLET_ADDRESS not set.")

        from eth_account import Account

        account = Account.from_key(self._private_key)
        signed = account.sign_message(message)
        return {
            "signature": signed.signature.hex(),
            "address": account.address,
            "message_hash": signed.messageHash.hex(),
        }

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def _is_checksum_address(addr: str) -> bool:
        """Check if address is a valid EVM checksum address."""
        if not addr.startswith("0x") or len(addr) != 42:
            return False
        try:
            from web3 import Web3

            return Web3.is_checksum_address(addr)
        except Exception:
            return False
