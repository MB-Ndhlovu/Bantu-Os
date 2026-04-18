"""
MessagingService tool schemas.
Each schema follows the kernel tool executor format.
"""
from __future__ import annotations

TOOL_SCHEMAS = {
    "messaging_send_email": {
        "description": "Send an email via SMTP.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "The recipient's email address.",
                },
                "subject": {
                    "type": "string",
                    "description": "The email subject line.",
                },
                "body": {
                    "type": "string",
                    "description": "The plain-text email body.",
                },
                "from_addr": {
                    "type": "string",
                    "description": (
                        "The sender address. Defaults to the configured "
                        "SMTP_DEFAULT_FROM address."
                    ),
                    "nullable": True,
                },
            },
            "required": ["to", "subject", "body"],
        },
    },
    "messaging_send_sms": {
        "description": "Send an SMS via Twilio.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "The recipient's phone number in E.164 format (e.g. +27612345678).",
                },
                "body": {
                    "type": "string",
                    "description": "The SMS body text (max 1600 characters).",
                },
            },
            "required": ["to", "body"],
        },
    },
    "messaging_send_telegram": {
        "description": "Send a message via a Telegram bot.",
        "parameters": {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "string",
                    "description": (
                        "The Telegram chat ID. Use 'me' to send to yourself, "
                        "or a numeric chat ID for group/private chats."
                    ),
                },
                "text": {
                    "type": "string",
                    "description": "The message text (max 4096 characters).",
                },
            },
            "required": ["chat_id", "text"],
        },
    },
}
