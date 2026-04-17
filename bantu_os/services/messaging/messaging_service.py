# pyright: reportMissingTypeStubs=false
# ruff: noqa: ERA001

'''
MessagingService — Phase 2 skeleton.

Unified messaging service for email (SMTP), SMS (Twilio), and Telegram.
Exposes three tools to the Bantu-OS kernel via `use_tool_async`:

    messaging_send_email    — send via SMTP
    messaging_send_sms      — send via Twilio
    messaging_send_telegram — send via Telegram bot

Env vars required:
    SMTP_PASSWORD       sender email password (use an app password for Gmail)
    TWILIO_AUTH_TOKEN   Twilio account auth token
    TELEGRAM_BOT_TOKEN  Telegram bot token from @BotFather

Usage:
    from bantu_os.services.messaging import MessagingService

    svc = MessagingService()
    result = await svc.use_tool_async(
        'messaging_send_email',
        {'to': 'user@example.com', 'subject': 'Hello', 'body': 'Hi there'}
    )
'''
from __future__ import annotations

import pytest
from typing import Any, Dict, Optional
from bantu_os.services.service_base import ServiceBase


class MessagingService(ServiceBase):
    '''
    Unified messaging service for email, SMS, and Telegram.

    Each tool method is a coroutine stub that will be implemented in a
    subsequent phase.  The service is registered with the kernel through
    the `tool_schema` property.

    Example
    -------
    >>> svc = MessagingService()
    >>> svc.tool_schema['messaging_send_email']
    {'description': 'Send an email via SMTP.', ...}
    '''

    def __init__(self) -> None:
        '''Initialise the service with an empty provider registry.'''
        super().__init__(name='messaging')
        self._providers: Dict[str, Any] = {}

    def health_check(self) -> Dict[str, Any]:
        '''Return a basic health status dict.'''
        return {'status': 'ok', 'service': self.name}

    @property
    def tool_schema(self) -> Dict[str, Any]:
        '''
        Return the JSON schema for all messaging tools exposed by this service.

        Schema is defined in bantu_os.services.messaging.schemas.TOOL_SCHEMAS.
        '''
        from bantu_os.services.messaging import schemas as _schemas
        return _schemas.TOOL_SCHEMAS  # type: ignore[no-any-return]

    async def use_tool_async(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        '''
        Dispatch a named tool to its implementation method.

        Parameters
        ----------
        tool_name : str
            One of ``messaging_send_email``, ``messaging_send_sms``,
            ``messaging_send_telegram``.
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
            'messaging_send_email':    self.messaging_send_email,
            'messaging_send_sms':      self.messaging_send_sms,
            'messaging_send_telegram': self.messaging_send_telegram,
        }
        if tool_name not in _dispatch:
            raise ValueError(f'[MessagingService] Unknown tool: {tool_name!r}')
        return await _dispatch[tool_name](**params)

    # ─── Tool stubs (implement in next phase) ────────────────────

    async def messaging_send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_addr: Optional[str] = None,
    ) -> Dict[str, Any]:
        '''
        Send an email via SMTP.

        Parameters
        ----------
        to : str
            Recipient email address.
        subject : str
            Email subject line.
        body : str
            Plain-text email body.
        from_addr : str, optional
            Override the configured sender address.

        Returns
        -------
        dict
            ``{'message_id': '<smtp-id>'}`` on success.
        '''
        pytest.skip('messaging_send_email not yet implemented')  # noqa: S607

    async def messaging_send_sms(
        self,
        to: str,
        body: str,
    ) -> Dict[str, Any]:
        '''
        Send an SMS via Twilio.

        Parameters
        ----------
        to : str
            Recipient phone number in E.164 format (e.g. ``+27612345678``).
        body : str
            SMS body (max 1 600 characters).

        Returns
        -------
        dict
            ``{'sid': '<twilio-sid>', 'status': '<status>'}`` on success.
        '''
        pytest.skip('messaging_send_sms not yet implemented')  # noqa: S607

    async def messaging_send_telegram(
        self,
        chat_id: str,
        text: str,
    ) -> Dict[str, Any]:
        '''
        Send a message via a Telegram bot.

        Parameters
        ----------
        chat_id : str
            Telegram chat ID.  Use ``'me'`` for the bot's own chat,
            or a numeric chat ID for groups and other users.
        text : str
            Message text (max 4 096 characters).

        Returns
        -------
        dict
            ``{'message_id': <int>}`` on success.
        '''
        pytest.skip('messaging_send_telegram not yet implemented')  # noqa: S607