"""
FintechService — Phase 2 skeleton.
Handles Stripe, M-Pesa, Flutterwave, and Paystack payments.

TOOLS (not yet implemented):
  - fintech_create_payment (Stripe)
  - fintech_check_balance
  - fintech_request_mpesa
  - fintech_request_flutterwave
  - fintech_request_paystack
"""
from __future__ import annotations

import pytest
from typing import Any, Dict, Optional
from bantu_os.services.service_base import ServiceBase


class FintechService(ServiceBase):
    """Payment and financial transaction service."""

    def __init__(self) -> None:
        super().__init__(name="fintech")
        self._providers: Dict[str, Any] = {}

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "service": self.name}

    # ─── Tool stubs (implement in next phase) ────────────────────

    async def fintech_create_payment(
        self,
        amount: int,
        currency: str,
        customer_email: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        pytest.skip("fintech_create_payment not yet implemented")

    async def fintech_check_balance(
        self,
        provider: str = "stripe",
    ) -> Dict[str, Any]:
        pytest.skip("fintech_check_balance not yet implemented")

    async def fintech_request_mpesa(
        self,
        phone: str,
        amount: int,
        reference: str,
    ) -> Dict[str, Any]:
        pytest.skip("fintech_request_mpesa not yet implemented")

    async def fintech_request_flutterwave(
        self,
        amount: int,
        currency: str,
        reference: str,
    ) -> Dict[str, Any]:
        pytest.skip("fintech_request_flutterwave not yet implemented")

    async def fintech_request_paystack(
        self,
        amount: int,
        email: str,
        reference: str,
    ) -> Dict[str, Any]:
        pytest.skip("fintech_request_paystack not yet implemented")

    @property
    def tool_schema(self) -> Dict[str, Any]:
        return {
            "fintech_create_payment": {
                "description": "Create a payment using Stripe.",
                "parameters": {
                    "amount": {"type": "integer", "description": "The amount to charge."},
                    "currency": {"type": "string", "description": "The currency to charge in."},
                    "customer_email": {"type": "string", "description": "The customer's email address."},
                    "description": {"type": "string", "description": "A description of the payment.", "required": False},
                },
            },
            "fintech_check_balance": {
                "description": "Check the balance of a provider's account.",
                "parameters": {
                    "provider": {"type": "string", "description": "The provider to check the balance for.", "default": "stripe"},
                },
            },
            "fintech_request_mpesa": {
                "description": "Request a payment via M-Pesa.",
                "parameters": {
                    "phone": {"type": "string", "description": "The customer's phone number."},
                    "amount": {"type": "integer", "description": "The amount to charge."},
                    "reference": {"type": "string", "description": "A reference for the payment."},
                },
            },
            "fintech_request_flutterwave": {
                "description": "Request a payment via Flutterwave.",
                "parameters": {
                    "amount": {"type": "integer", "description": "The amount to charge."},
                    "currency": {"type": "string", "description": "The currency to charge in."},
                    "reference": {"type": "string", "description": "A reference for the payment."},
                },
            },
            "fintech_request_paystack": {
                "description": "Request a payment via Paystack.",
                "parameters": {
                    "amount": {"type": "integer", "description": "The amount to charge."},
                    "email": {"type": "string", "description": "The customer's email address."},
                    "reference": {"type": "string", "description": "A reference for the payment."},
                },
            },
        }