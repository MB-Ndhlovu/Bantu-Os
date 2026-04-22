"""
MessagingService — Phase 2.

Unified messaging service for email (SMTP), SMS (Twilio), and Telegram.
Exposes three tools to the Bantu-OS kernel via ``use_tool_async``:

    messaging_send_email    — send via SMTP
    messaging_send_sms      — send via Twilio
    messaging_send_telegram — send via Telegram bot

Env vars required:
    SMTP_HOST             SMTP server hostname (e.g. smtp.gmail.com)
    SMTP_PORT             SMTP port (default 587)
    SMTP_USERNAME         Sender email username / full address
    SMTP_PASSWORD         Sender email password (use an app password for Gmail)
    SMTP_DEFAULT_FROM     Default sender address
    TWILIO_ACCOUNT_SID   Twilio account SID
    TWILIO_AUTH_TOKEN    Twilio auth token
    TWILIO_FROM_NUMBER   Twilio phone number (E.164, e.g. +1234567890)
    TELEGRAM_BOT_TOKEN   Telegram bot token from @BotFather
"""

from __future__ import annotations

import asyncio
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

import aiohttp

from bantu_os.services.service_base import ServiceBase


class MessagingService(ServiceBase):
    """
    Unified messaging service for email, SMS, and Telegram.

    Each tool method calls the respective provider API asynchronously.
    """

    def __init__(self) -> None:
        super().__init__(name="messaging")
        self._smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self._smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self._smtp_username = os.getenv("SMTP_USERNAME", "")
        self._smtp_password = os.getenv("SMTP_PASSWORD", "")
        self._smtp_default_from = os.getenv("SMTP_DEFAULT_FROM", "")
        self._twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self._twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self._twilio_from = os.getenv("TWILIO_FROM_NUMBER", "")
        self._telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": self.name,
            "email_configured": bool(self._smtp_username and self._smtp_password),
            "sms_configured": bool(
                self._twilio_account_sid
                and self._twilio_auth_token
                and self._twilio_from
            ),
            "telegram_configured": bool(self._telegram_token),
        }

    # -------------------------------------------------------------------------
    # Tool dispatcher
    # -------------------------------------------------------------------------

    async def use_tool_async(
        self, tool_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Dispatch a named tool to its implementation method."""
        dispatch: dict[str, Any] = {
            "messaging_send_email": self.messaging_send_email,
            "messaging_send_sms": self.messaging_send_sms,
            "messaging_send_telegram": self.messaging_send_telegram,
        }
        if tool_name not in dispatch:
            raise ValueError(f"[MessagingService] Unknown tool: {tool_name!r}")
        return await dispatch[tool_name](**params)

    # -------------------------------------------------------------------------
    # Email (SMTP)
    # -------------------------------------------------------------------------

    async def messaging_send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_addr: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an email via SMTP.

        Uses stdlib smtplib in a thread pool to avoid blocking the event loop.
        """
        if not self._smtp_username or not self._smtp_password:
            raise EnvironmentError(
                "SMTP_USERNAME / SMTP_PASSWORD not set. " "Cannot send email."
            )

        from_addr = from_addr or self._smtp_default_from or self._smtp_username

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to

        text_part = MIMEText(body, "plain", "utf-8")
        msg.attach(text_part)

        def _send() -> str:
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self._smtp_username, self._smtp_password)
                server.sendmail(from_addr, [to], msg.as_string())
            return f"Message sent to {to}"

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _send)
        self._log_operation("send_email", {"to": to, "subject": subject})
        return {"message_id": result}

    # -------------------------------------------------------------------------
    # SMS (Twilio)
    # -------------------------------------------------------------------------

    async def messaging_send_sms(
        self,
        to: str,
        body: str,
    ) -> dict[str, Any]:
        """
        Send an SMS via Twilio REST API.

        Docs: https://www.twilio.com/docs/sms/api/message-resource
        """
        if not all(
            [self._twilio_account_sid, self._twilio_auth_token, self._twilio_from]
        ):
            raise EnvironmentError(
                "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and "
                "TWILIO_FROM_NUMBER must all be set to send SMS."
            )

        url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{self._twilio_account_sid}/Messages.json"
        )
        payload = {
            "From": self._twilio_from,
            "To": to,
            "Body": body,
        }
        auth = aiohttp.BasicAuth(self._twilio_account_sid, self._twilio_auth_token)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload, auth=auth) as resp:
                data = await resp.json()
                if resp.status >= 400:
                    raise RuntimeError(
                        f"Twilio error {resp.status}: {data.get('message', data)}"
                    )
                self._log_operation("send_sms", {"to": to})
                return {
                    "sid": data.get("sid", ""),
                    "status": data.get("status", "queued"),
                }

    # -------------------------------------------------------------------------
    # Telegram
    # -------------------------------------------------------------------------

    async def messaging_send_telegram(
        self,
        chat_id: str,
        text: str,
    ) -> dict[str, Any]:
        """
        Send a message via a Telegram bot using the Bot API.

        chat_id can be:
          - 'me' — resolves to the bot's own chat ID (direct message to owner)
          - numeric string — a specific chat ID (user or group)
          - full '@username' — resolves to a channel/group

        Max text length: 4096 chars. Longer messages are truncated.
        """
        if not self._telegram_token:
            raise EnvironmentError(
                "TELEGRAM_BOT_TOKEN not set. Cannot send Telegram messages."
            )

        if chat_id.lower() == "me":
            # Bot cannot send to 'me' directly — get updates to find owner chat_id
            chat_id = await self._resolve_telegram_me()

        if len(text) > 4096:
            text = text[:4093] + "..."

        url = f"https://api.telegram.org/bot{self._telegram_token}/" f"sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    raise RuntimeError(
                        f"Telegram API error: {data.get('description', data)}"
                    )
                result = data.get("result", {})
                self._log_operation("send_telegram", {"chat_id": chat_id})
                return {"message_id": result.get("message_id", 0)}

    async def _resolve_telegram_me(self) -> str:
        """
        Get the bot's own chat ID by fetching updates.

        This is the bot's DM chat — we use it when the user passes 'me'.
        """
        url = f"https://api.telegram.org/bot{self._telegram_token}/" f"getUpdates"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    raise RuntimeError(
                        f"Telegram getUpdates error: {data.get('description', data)}"
                    )
                updates = data.get("result", [])
                if updates:
                    # First update's chat is the bot's DM conversation
                    return str(updates[0]["message"]["chat"]["id"])
                raise RuntimeError(
                    "No Telegram updates found. Start a chat with your bot first."
                )
