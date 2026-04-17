"""
FintechService tool schemas.
Covers Stripe, M-Pesa, Flutterwave, and Paystack.

Env vars required:
  STRIPE_SECRET_KEY        — Stripe secret key (sk_live_... or sk_test_...)
  MPESA_CONSUMER_KEY      — Safaricom M-Pesa API consumer key
  MPESA_CONSUMER_SECRET   — Safaricom M-Pesa API consumer secret
  MPESA_SHORTCODE         — Safaricom shortcode (paybill/till number)
  FLUTTERWAVE_SECRET_KEY  — Flutterwave secret key
  PAYSTACK_SECRET_KEY     — Paystack secret key
"""
from __future__ import annotations

TOOL_SCHEMAS = {
    "fintech_create_payment": {
        "description": "Create a Stripe checkout session for card/general payments.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "integer",
                    "description": (
                        "Amount to charge in the smallest currency unit "
                        "(e.g. cents for USD, kobo for ZAR)."
                    ),
                },
                "currency": {
                    "type": "string",
                    "description": (
                        "ISO 4217 currency code (e.g. 'usd', 'zar', 'kes')."
                    ),
                },
                "customer_email": {
                    "type": "string",
                    "description": "The customer's email address.",
                },
                "description": {
                    "type": "string",
                    "description": "A description shown on the checkout page.",
                    "nullable": True,
                },
            },
            "required": ["amount", "currency", "customer_email"],
        },
        "returns": {
            "type": "object",
            "properties": {
                "payment_url": {
                    "type": "string",
                    "description": "Stripe-hosted checkout URL to redirect the user.",
                },
                "session_id": {
                    "type": "string",
                    "description": "Stripe checkout session ID.",
                },
            },
        },
    },
    "fintech_check_balance": {
        "description": "Check the available balance on a connected provider account.",
        "parameters": {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string",
                    "description": "The provider name ('stripe', 'paystack', 'flutterwave').",
                    "default": "stripe",
                },
            },
            "required": [],
        },
        "returns": {
            "type": "object",
            "properties": {
                "available": {
                    "type": "number",
                    "description": "Available balance in major currency units.",
                },
                "currency": {
                    "type": "string",
                    "description": "ISO 4217 currency code.",
                },
            },
        },
    },
    "fintech_request_mpesa": {
        "description": (
            "Initiate an M-Pesa STK push (Lipa na M-Pesa). "
            "Polls for up to 30 seconds for payment confirmation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "phone": {
                    "type": "string",
                    "description": (
                        "Customer phone number in MSISDN format (e.g. 27612345678 "
                        "or +27612345678)."
                    ),
                },
                "amount": {
                    "type": "integer",
                    "description": "Amount in smallest currency unit (KES cents).",
                },
                "reference": {
                    "type": "string",
                    "description": "Payment reference (e.g. invoice or account number).",
                },
            },
            "required": ["phone", "amount", "reference"],
        },
        "returns": {
            "type": "object",
            "properties": {
                "checkout_request_id": {
                    "type": "string",
                    "description": "M-Pesa checkout request ID for status polling.",
                },
                "status": {
                    "type": "string",
                    "description": "'pending', 'completed', or 'failed'.",
                },
            },
        },
    },
    "fintech_request_flutterwave": {
        "description": "Initiate a Flutterwave payment request.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "integer",
                    "description": "Amount in smallest currency unit.",
                },
                "currency": {
                    "type": "string",
                    "description": "ISO 4217 currency code (e.g. 'NGN', 'KES', 'ZAR').",
                },
                "reference": {
                    "type": "string",
                    "description": "Unique payment reference.",
                },
            },
            "required": ["amount", "currency", "reference"],
        },
        "returns": {
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Flutterwave transaction reference.",
                },
                "payment_url": {
                    "type": "string",
                    "description": "Flutterwave hosted payment page URL.",
                },
            },
        },
    },
    "fintech_request_paystack": {
        "description": "Initialize a Paystack transaction.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "integer",
                    "description": "Amount in kobo (smallest currency unit, e.g. 5000 = 50 NGN).",
                },
                "email": {
                    "type": "string",
                    "description": "Customer email address.",
                },
                "reference": {
                    "type": "string",
                    "description": "Unique payment reference.",
                },
            },
            "required": ["amount", "email", "reference"],
        },
        "returns": {
            "type": "object",
            "properties": {
                "authorization_url": {
                    "type": "string",
                    "description": "Paystack hosted checkout URL.",
                },
                "reference": {
                    "type": "string",
                    "description": "Paystack transaction reference.",
                },
            },
        },
    },
}