# pyright: reportMissingTypeStubs=false
# ruff: noqa: ERA001

'''
FintechService — Phase 2 skeleton.

Payment and financial transaction service covering:
    Stripe   — card / general checkout
    M-Pesa   — Safaricom mobile money (Kenya)
    Flutterwave — pan-African payments
    Paystack  — Nigerian payments

Exposes five tools to the Bantu-OS kernel via ``use_tool_async``:

    fintech_create_payment
    fintech_check_balance
    fintech_request_mpesa
    fintech_request_flutterwave
    fintech_request_paystack

Env vars required:
    STRIPE_SECRET_KEY         Stripe secret key
    MPESA_CONSUMER_KEY       Safaricom M-Pesa consumer key
    MPESA_CONSUMER_SECRET    Safaricom M-Pesa consumer secret
    MPESA_SHORTCODE          Safaricom paybill/till number
    FLUTTERWAVE_SECRET_KEY   Flutterwave secret key
    PAYSTACK_SECRET_KEY      Paystack secret key

Usage:
    from bantu_os.services.fintech import FintechService

    svc = FintechService()
    result = await svc.use_tool_async(
        'fintech_request_mpesa',
        {'phone': '+254712345678', 'amount': 100, 'reference': 'INV-001'}
    )
'''
from __future__ import annotations

import pytest
from typing import Any, Dict, Optional
from bantu_os.services.service_base import ServiceBase


class FintechService(ServiceBase):
    '''
    Payment and financial transaction service.

    Each tool method is a coroutine stub that will be implemented in a
    subsequent phase.  The service is registered with the kernel through
    the ``tool_schema`` property.
    '''

    def __init__(self) -> None:
        '''Initialise the service with an empty provider registry.'''
        super().__init__(name='fintech')
        self._providers: Dict[str, Any] = {}

    def health_check(self) -> Dict[str, Any]:
        '''Return a basic health status dict.'''
        return {'status': 'ok', 'service': self.name}

    @property
    def tool_schema(self) -> Dict[str, Any]:
        '''
        Return the JSON schema for all fintech tools exposed by this service.

        Schema is defined in bantu_os.services.fintech.schemas.TOOL_SCHEMAS.
        '''
        from bantu_os.services.fintech import schemas as _schemas
        return _schemas.TOOL_SCHEMAS  # type: ignore[no-any-return]

    async def use_tool_async(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        '''
        Dispatch a named tool to its implementation method.

        Parameters
        ----------
        tool_name : str
            One of: ``fintech_create_payment``, ``fintech_check_balance``,
            ``fintech_request_mpesa``, ``fintech_request_flutterwave``,
            ``fintech_request_paystack``.
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
            'fintech_create_payment':     self.fintech_create_payment,
            'fintech_check_balance':      self.fintech_check_balance,
            'fintech_request_mpesa':      self.fintech_request_mpesa,
            'fintech_request_flutterwave': self.fintech_request_flutterwave,
            'fintech_request_paystack':   self.fintech_request_paystack,
        }
        if tool_name not in _dispatch:
            raise ValueError(f'[FintechService] Unknown tool: {tool_name!r}')
        return await _dispatch[tool_name](**params)

    # ─── Tool stubs (implement in next phase) ────────────────────

    async def fintech_create_payment(
        self,
        amount: int,
        currency: str,
        customer_email: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        '''
        Create a Stripe checkout session for card-based payments.

        Parameters
        ----------
        amount : int
            Amount in the smallest currency unit (e.g. cents for USD).
        currency : str
            ISO 4217 currency code (e.g. ``'usd'``, ``'zar'``).
        customer_email : str
            Customer's email address.
        description : str, optional
            Payment description shown on the checkout page.

        Returns
        -------
        dict
            ``{'payment_url': '<stripe-url>', 'session_id': '<id>'}`` on success.
        '''
        pytest.skip('fintech_create_payment not yet implemented')  # noqa: S607

    async def fintech_check_balance(
        self,
        provider: str = 'stripe',
    ) -> Dict[str, Any]:
        '''
        Check the available balance on a connected provider account.

        Parameters
        ----------
        provider : str
            Provider name: ``'stripe'``, ``'paystack'``, or ``'flutterwave'``.
            Defaults to ``'stripe'``.

        Returns
        -------
        dict
            ``{'available': <float>, 'currency': '<code>'}`` on success.
        '''
        pytest.skip('fintech_check_balance not yet implemented')  # noqa: S607

    async def fintech_request_mpesa(
        self,
        phone: str,
        amount: int,
        reference: str,
    ) -> Dict[str, Any]:
        '''
        Initiate an M-Pesa STK push (Lipa na M-Pesa).

        Polls the Safaricom API for up to 30 seconds for payment confirmation.

        Parameters
        ----------
        phone : str
            Customer phone number in MSISDN format
            (e.g. ``'0712345678'`` or ``'+254712345678'``).
        amount : int
            Amount in KES cents.
        reference : str
            Payment reference (e.g. invoice or account number).

        Returns
        -------
        dict
            ``{'checkout_request_id': '<id>', 'status': 'pending'}`` initially;
            ``{'status': 'completed' | 'failed'}`` after polling.
        '''
        pytest.skip('fintech_request_mpesa not yet implemented')  # noqa: S607

    async def fintech_request_flutterwave(
        self,
        amount: int,
        currency: str,
        reference: str,
    ) -> Dict[str, Any]:
        '''
        Initiate a Flutterwave payment request.

        Parameters
        ----------
        amount : int
            Amount in the smallest currency unit.
        currency : str
            ISO 4217 currency code (e.g. ``'NGN'``, ``'KES'``, ``'ZAR'``).
        reference : str
            Unique payment reference.

        Returns
        -------
        dict
            ``{'reference': '<id>', 'payment_url': '<url>'}`` on success.
        '''
        pytest.skip('fintech_request_flutterwave not yet implemented')  # noqa: S607

    async def fintech_request_paystack(
        self,
        amount: int,
        email: str,
        reference: str,
    ) -> Dict[str, Any]:
        '''
        Initialize a Paystack transaction.

        Parameters
        ----------
        amount : int
            Amount in kobo (smallest currency unit; e.g. ``5000`` = 50 NGN).
        email : str
            Customer's email address.
        reference : str
            Unique payment reference.

        Returns
        -------
        dict
            ``{'authorization_url': '<url>', 'reference': '<id>'}`` on success.
        '''
        pytest.skip('fintech_request_paystack not yet implemented')  # noqa: S607