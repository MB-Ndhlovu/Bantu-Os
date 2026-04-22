"""
FintechService — Phase 2.

Payment and financial transaction service covering:
    Stripe      — card / general checkout
    M-Pesa      — Safaricom mobile money (Kenya)
    Flutterwave — pan-African payments
    Paystack    — Nigerian payments

Exposes five tools to the Bantu-OS kernel via ``use_tool_async``:

    fintech_create_payment       — create a Stripe checkout session
    fintech_check_balance       — check connected account balance
    fintech_request_mpesa        — initiate M-Pesa STK push
    fintech_request_flutterwave  — initiate Flutterwave payment
    fintech_request_paystack     — initialize Paystack transaction

Env vars required:
    STRIPE_SECRET_KEY       Stripe secret key (sk_live_... or sk_test_...)
    STRIPE_WEBHOOK_SECRET   Stripe webhook signing secret (whsec_...)
    MPESA_CONSUMER_KEY    Safaricom M-Pesa consumer key
    MPESA_CONSUMER_SECRET Safaricom M-Pesa consumer secret
    MPESA_SHORTCODE       Safaricom paybill/till number
    MPESA_PASSKEY         Safaricom Lipa Na M-Pesa online passkey
    MPESACallback_URL      Your callback URL (for STK push)
    FLUTTERWAVE_SECRET_KEY Flutterwave secret key
    PAYSTACK_SECRET_KEY    Paystack secret key
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import aiohttp


class FintechService:
    """Payment and financial transaction service."""

    def __init__(self) -> None:
        self._stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
        self._mpesa_consumer_key = os.getenv("MPESA_CONSUMER_KEY", "")
        self._mpesa_consumer_secret = os.getenv("MPESA_CONSUMER_SECRET", "")
        self._mpesa_shortcode = os.getenv("MPESA_SHORTCODE", "")
        self._mpesa_passkey = os.getenv("MPESA_PASSKEY", "")
        self._mpesa_callback_url = os.getenv("MPESA_CALLBACK_URL", "")
        self._flutterwave_key = os.getenv("FLUTTERWAVE_SECRET_KEY", "")
        self._paystack_key = os.getenv("PAYSTACK_SECRET_KEY", "")

        # Cached M-Pesa OAuth token
        self._mpesa_token: str | None = None
        self._mpesa_token_expires_at: float = 0

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "fintech",
            "stripe_configured": bool(self._stripe_key),
            "mpesa_configured": bool(
                self._mpesa_consumer_key
                and self._mpesa_consumer_secret
                and self._mpesa_shortcode
            ),
            "flutterwave_configured": bool(self._flutterwave_key),
            "paystack_configured": bool(self._paystack_key),
        }

    # -------------------------------------------------------------------------
    # Tool dispatcher
    # -------------------------------------------------------------------------

    async def use_tool_async(
        self, tool_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Dispatch a named tool to its implementation method."""
        dispatch: dict[str, Any] = {
            "fintech_create_payment": self.fintech_create_payment,
            "fintech_check_balance": self.fintech_check_balance,
            "fintech_request_mpesa": self.fintech_request_mpesa,
            "fintech_request_flutterwave": self.fintech_request_flutterwave,
            "fintech_request_paystack": self.fintech_request_paystack,
        }
        if tool_name not in dispatch:
            raise ValueError(f"[FintechService] Unknown tool: {tool_name!r}")
        return await dispatch[tool_name](**params)

    # -------------------------------------------------------------------------
    # Stripe
    # -------------------------------------------------------------------------

    async def fintech_create_payment(
        self,
        amount: int,
        currency: str,
        customer_email: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a Stripe checkout session for card-based payments.

        Returns a payment URL the user visits to complete payment.
        After payment, Stripe calls your webhook with the checkout.session.completed event.
        """
        if not self._stripe_key:
            raise EnvironmentError("STRIPE_SECRET_KEY not set.")

        import stripe

        stripe.api_key = self._stripe_key

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": currency.lower(),
                        "product_data": {
                            "name": description or "Bantu-OS Payment",
                        },
                        "unit_amount": amount,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url="https://bantu-os.local/payment/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://bantu-os.local/payment/cancelled",
            customer_email=customer_email,
            metadata={"description": description or ""},
        )

        return {
            "payment_url": session.url or "",
            "session_id": session.id,
        }

    async def fintech_check_balance(
        self,
        provider: str = "stripe",
    ) -> dict[str, Any]:
        """
        Check available balance on a connected provider account.
        """
        if provider == "stripe":
            return await self._stripe_balance()
        elif provider == "paystack":
            return await self._paystack_balance()
        elif provider == "flutterwave":
            return await self._flutterwave_balance()
        else:
            raise ValueError(f"Unknown provider: {provider!r}")

    async def _stripe_balance(self) -> dict[str, Any]:
        import stripe

        stripe.api_key = self._stripe_key
        balance = stripe.Balance.retrieve()
        available = balance.available
        return {
            "available": sum(a["amount"] for a in available),
            "currency": available[0]["currency"] if available else "usd",
            "provider": "stripe",
        }

    # -------------------------------------------------------------------------
    # M-Pesa
    # -------------------------------------------------------------------------

    async def fintech_request_mpesa(
        self,
        phone: str,
        amount: int,
        reference: str,
    ) -> dict[str, Any]:
        """
        Initiate an M-Pesa STK push (Lipa na M-Pesa Online).

        Prompts the customer phone with an LNM popup to approve payment.
        Polls Safaricom API for up to 60 seconds for confirmation.
        """
        if not all(
            [
                self._mpesa_consumer_key,
                self._mpesa_consumer_secret,
                self._mpesa_shortcode,
            ]
        ):
            raise EnvironmentError(
                "MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET, "
                "and MPESA_SHORTCODE must all be set."
            )

        token = await self._mpesa_get_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Normalize phone to MSISDN format (254...)
        phone = self._normalize_msisdn(phone)

        import base64
        import datetime as dt

        timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
        passkey_str = f"{self._mpesa_shortcode}{self._mpesa_passkey}{timestamp}"
        passkey_b64 = base64.b64encode(passkey_str.encode()).decode()

        payload = {
            "BusinessShortCode": self._mpesa_shortcode,
            "Password": passkey_b64,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(amount),
            "PartyA": phone,
            "PartyB": self._mpesa_shortcode,
            "PhoneNumber": phone,
            "CallBackURL": self._mpesa_callback_url
            or "https://bantu-os.local/mpesa/callback",
            "AccountReference": reference,
            "TransactionDesc": f"Payment {reference}",
        }

        url = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                data = await resp.json()
                if resp.status >= 400:
                    raise RuntimeError(
                        f"M-Pesa error: {data.get('errorMessage', data)}"
                    )
                checkout_id = data.get("CheckoutRequestID", "")
                # Poll for confirmation
                status = await self._mpesa_poll(checkout_id, phone, headers)
                return {
                    "checkout_request_id": checkout_id,
                    "status": status,
                    "reference": reference,
                }

    async def _mpesa_get_token(self) -> str:
        """Get (and cache) an M-Pesa OAuth token."""
        now = time.time()
        if self._mpesa_token and now < self._mpesa_token_expires_at:
            return self._mpesa_token

        url = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        auth = aiohttp.BasicAuth(self._mpesa_consumer_key, self._mpesa_consumer_secret)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=auth) as resp:
                data = await resp.json()
                if resp.status >= 400:
                    raise RuntimeError(f"M-Pesa auth error: {data}")
                self._mpesa_token = data["access_token"]
                self._mpesa_token_expires_at = now + data.get("expires_in", 3600) - 60
                return self._mpesa_token

    async def _mpesa_poll(
        self,
        checkout_id: str,
        phone: str,
        headers: dict[str, str],
        *,
        max_wait: int = 60,
    ) -> str:
        """Poll M-Pesa for transaction result."""
        url = "https://api.safaricom.co.ke/mpesa/stkpush/v1/query"
        import datetime as dt

        timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
        import base64

        passkey_str = f"{self._mpesa_shortcode}{self._mpesa_passkey}{timestamp}"
        passkey_b64 = base64.b64encode(passkey_str.encode()).decode()

        payload = {
            "BusinessShortCode": self._mpesa_shortcode,
            "Password": passkey_b64,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_id,
        }

        deadline = time.time() + max_wait
        while time.time() < deadline:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    data = await resp.json()
                    result_code = data.get("ResultCode")
                    if result_code is None:
                        await asyncio.sleep(2)
                        continue
                    if result_code == 0:
                        return "completed"
                    return f"failed:code_{result_code}"
            await asyncio.sleep(2)
        return "timeout"

    @staticmethod
    def _normalize_msisdn(phone: str) -> str:
        """Convert a phone number to M-Pesa MSISDN format (254...)."""
        digits = "".join(c for c in phone if c.isdigit())
        if digits.startswith("0"):
            digits = "254" + digits[1:]
        elif not digits.startswith("254"):
            digits = "254" + digits
        return digits

    # -------------------------------------------------------------------------
    # Flutterwave
    # -------------------------------------------------------------------------

    async def fintech_request_flutterwave(
        self,
        amount: int,
        currency: str,
        reference: str,
        customer_email: str | None = None,
    ) -> dict[str, Any]:
        """
        Initiate a Flutterwave payment request.

        Returns a payment link the customer uses to complete payment.
        """
        if not self._flutterwave_key:
            raise EnvironmentError("FLUTTERWAVE_SECRET_KEY not set.")

        url = "https://api.flutterwave.com/v3/payments"
        headers = {
            "Authorization": f"Bearer {self._flutterwave_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "tx_ref": reference,
            "amount": amount,
            "currency": currency.upper(),
            "redirect_url": "https://bantu-os.local/payment/fluttewave/return",
            "meta": {"reference": reference},
            "customer": {
                "email": customer_email or "",
                "phonenumber": "",
                "name": "",
            },
            "customizations": {
                "title": "Bantu-OS",
                "description": f"Payment {reference}",
            },
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                data = await resp.json()
                if data.get("status") != "success":
                    raise RuntimeError(
                        f"Flutterwave error: {data.get('message', data)}"
                    )
                link = data.get("data", {}).get("link", "")
                return {"reference": reference, "payment_url": link}

    async def _flutterwave_balance(self) -> dict[str, Any]:
        url = "https://api.flutterwave.com/v3/balances"
        headers = {
            "Authorization": f"Bearer {self._flutterwave_key}",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                if data.get("status") != "success":
                    return {"error": data.get("message", "failed")}
                balances = data.get("data", [])
                return {
                    "available": (
                        balances[0].get("available_balance", 0) if balances else 0
                    ),
                    "currency": balances[0].get("currency", "") if balances else "",
                    "provider": "flutterwave",
                }

    # -------------------------------------------------------------------------
    # Paystack
    # -------------------------------------------------------------------------

    async def fintech_request_paystack(
        self,
        amount: int,
        email: str,
        reference: str | None = None,
    ) -> dict[str, Any]:
        """
        Initialize a Paystack transaction.

        Returns an authorization URL for the customer to complete payment.
        amount is in kobo (1/100 of the major currency unit).
        """
        if not self._paystack_key:
            raise EnvironmentError("PAYSTACK_SECRET_KEY not set.")

        url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {self._paystack_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "amount": amount,
            "email": email,
            "reference": reference or f"bantu_{int(time.time())}",
            "callback_url": "https://bantu-os.local/payment/paystack/return",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                data = await resp.json()
                if not data.get("status"):
                    raise RuntimeError(f"Paystack error: {data.get('message', data)}")
                result = data.get("data", {})
                return {
                    "authorization_url": result.get("authorization_url", ""),
                    "reference": result.get("reference", ""),
                }

    async def _paystack_balance(self) -> dict[str, Any]:
        url = "https://api.paystack.co/balance"
        headers = {"Authorization": f"Bearer {self._paystack_key}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                if not data.get("status"):
                    return {"error": data.get("message", "failed")}
                balances = data.get("data", [])
                return {
                    "available": balances[0].get("balance", 0) if balances else 0,
                    "currency": balances[0].get("currency", "") if balances else "",
                    "provider": "paystack",
                }
