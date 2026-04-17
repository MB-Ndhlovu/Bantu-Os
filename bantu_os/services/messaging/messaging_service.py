"""
MessagingService — Phase 2 skeleton.
Handles email (SMTP), SMS (Twilio), and Telegram messaging.

TOOLS (not yet implemented):
  - messaging_send_email
  - messaging_send_sms
  - messaging_send_telegram
"""
from __future__ import annotations

import pytest
from typing import Any, Dict, List, Optional
from bantu_os.services.service_base import ServiceBase


class MessagingService(ServiceBase):
    """Unified messaging service for email, SMS, and Telegram."""

    def __init__(self) -> None:
        super().__init__(name="messaging")
        self._providers: Dict[str, Any] = {}

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "service": self.name}

    @property
    def tool_schema(self) -> Dict[str, Any]:
        return {
            "messaging_send_email": {
                "description": "Send an email message.",
                "parameters": {
                    "to": {"type": "string", "description": "The recipient's email address."},
                    "subject": {"type": "string", "description": "The subject of the email."},
                    "body": {"type": "string", "description": "The body of the email."},
                    "from_addr": {
                        "type": "string",
                        "description": "The sender's email address. If not provided, the default sender address will be used.",
                        "required": False,
                    },
                },
            },
            "messaging_send_sms": {
                "description": "Send an SMS message.",
                "parameters": {
                    "to": {"type": "string", "description": "The recipient's phone number."},
                    "body": {"type": "string", "description": "The body of the SMS."},
                },
            },
            "messaging_send_telegram": {
                "description": "Send a message to a Telegram chat.",
                "parameters": {
                    "chat_id": {"type": "string", "description": "The ID of the Telegram chat."},
                    "text": {"type": "string", "description": "The text of the message."},
                },
            },
        }

    # ─── Tool stubs (implement in next phase) ────────────────────

    async def messaging_send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_addr: Optional[str] = None,
    ) -> Dict[str, Any]:
        pytest.skip("messaging_send_email not yet implemented")

    async def messaging_send_sms(
        self,
        to: str,
        body: str,
    ) -> Dict[str, Any]:
        pytest.skip("messaging_send_sms not yet implemented")

    async def messaging_send_telegram(
        self,
        chat_id: str,
        text: str,
    ) -> Dict[str, Any]:
        pytest.skip("messaging_send_telegram not yet implemented")