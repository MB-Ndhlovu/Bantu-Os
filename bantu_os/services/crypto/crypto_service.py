# pyright: reportMissingTypeStubs=false
# ruff: noqa: ERA001

'''
CryptoWalletService — Phase 2 skeleton.

EVM-compatible wallet service: balance queries, token transfers, message signing.
Supports Ethereum, Polygon, Base, and Binance Smart Chain.

Exposes three tools to the Bantu-OS kernel via ``use_tool_async``:

    crypto_get_balance   — query wallet balance (native or ERC-20)
    crypto_send          — transfer native tokens or ERC-20 tokens
    crypto_sign_message  — sign an arbitrary message with the wallet key

Env vars required:
    ETHEREUM_RPC_URL            RPC endpoint URL (Infura / Alchemy / etc.)
    CRYPTO_WALLET_PRIVATE_KEY   Wallet private key (encrypted at rest via secrets.py)
    CRYPTO_WALLET_ADDRESS       Default wallet address (EOA)

Supported networks:
    ethereum  — Ethereum Mainnet (chain-id: 1)
    polygon   — Polygon PoS (chain-id: 137)
    base      — Base (chain-id: 8453)
    bsc       — Binance Smart Chain (chain-id: 56)

Usage:
    from bantu_os.services.crypto import CryptoWalletService

    svc = CryptoWalletService()
    result = await svc.use_tool_async(
        'crypto_get_balance',
        {'address': '0x...', 'network': 'ethereum', 'token': None}
    )
'''
from __future__ import annotations

import pytest
from typing import Any, Dict, Optional
from bantu_os.services.service_base import ServiceBase


class CryptoWalletService(ServiceBase):
    '''
    EVM wallet service for balance queries, token transfers, and message signing.

    Supported networks: Ethereum, Polygon, Base, Binance Smart Chain.
    Each tool method is a coroutine stub that will be implemented in a
    subsequent phase.  The service is registered with the kernel through
    the ``tool_schema`` property.
    '''

    SUPPORTED_NETWORKS: list[str] = ['ethereum', 'polygon', 'base', 'bsc']

    def __init__(self) -> None:
        '''Initialise the service with no web3 client yet.'''
        super().__init__(name='crypto')
        self._web3: Optional[Any] = None

    def health_check(self) -> Dict[str, Any]:
        '''Return a basic health status dict.'''
        return {'status': 'ok', 'service': self.name}

    @property
    def tool_schema(self) -> Dict[str, Any]:
        '''
        Return the JSON schema for all crypto tools exposed by this service.

        Schema is defined in bantu_os.services.crypto.schemas.TOOL_SCHEMAS.
        '''
        from bantu_os.services.crypto import schemas as _schemas
        return _schemas.TOOL_SCHEMAS  # type: ignore[no-any-return]

    async def use_tool_async(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        '''
        Dispatch a named tool to its implementation method.

        Parameters
        ----------
        tool_name : str
            One of: ``crypto_get_balance``, ``crypto_send``,
            ``crypto_sign_message``.
        params : dict
            Tool-specific parameters (see tool_schema for definitions).

        Returns
        -------
        dict
            Tool-specific result.

        Raises
        ------
        ValueError
            If ``tool_name`` is not recognised.
        '''
        _dispatch: Dict[str, Any] = {
            'crypto_get_balance':   self.crypto_get_balance,
            'crypto_send':          self.crypto_send,
            'crypto_sign_message':  self.crypto_sign_message,
        }
        if tool_name not in _dispatch:
            raise ValueError(f'[CryptoWalletService] Unknown tool: {tool_name!r}')
        return await _dispatch[tool_name](**params)

    # ─── Tool stubs (implement in next phase) ────────────────────

    async def crypto_get_balance(
        self,
        address: Optional[str] = None,
        network: str = 'ethereum',
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        '''
        Query the balance of a wallet address on an EVM network.

        Parameters
        ----------
        address : str, optional
            Wallet address (0x...).  Defaults to ``CRYPTO_WALLET_ADDRESS``.
        network : str
            EVM network name.  Must be one of ``SUPPORTED_NETWORKS``.
            Defaults to ``'ethereum'``.
        token : str, optional
            ERC-20 token contract address.  If omitted, returns native
            currency balance.

        Returns
        -------
        dict
            ``{'balance': '<wei>', 'balance_human': '<eth>', 'symbol': '<SYM>', 'decimals': <n>}``.
        '''
        pytest.skip('crypto_get_balance not yet implemented')  # noqa: S607

    async def crypto_send(
        self,
        to: str,
        amount: str,
        network: str = 'ethereum',
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        '''
        Send native currency or an ERC-20 token to another address.

        Gas is estimated before sending; the kernel prompts the user for
        confirmation before proceeding.

        Parameters
        ----------
        to : str
            Recipient wallet address (0x...).
        amount : str
            Amount in the smallest unit (wei for ETH).  Verify balance first
            with ``crypto_get_balance``.
        network : str
            EVM network name.  Defaults to ``'ethereum'``.
        token : str, optional
            ERC-20 contract address.  If omitted, sends native currency.

        Returns
        -------
        dict
            ``{'tx_hash': '0x...', 'status': 'submitted'}`` on success.
        '''
        pytest.skip('crypto_send not yet implemented')  # noqa: S607

    async def crypto_sign_message(
        self,
        message: str,
        address: Optional[str] = None,
    ) -> Dict[str, Any]:
        '''
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
            ``{'signature': '0x...', 'address': '0x...'}`` on success.
        '''
        pytest.skip('crypto_sign_message not yet implemented')  # noqa: S607