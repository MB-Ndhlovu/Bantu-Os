from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import aiohttp

from .base import LLMProvider, ChatMessage, GenerateResult


class OpenRouterProvider(LLMProvider):
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: str = 'https://openrouter.ai/api/v1',
        **kwargs: Any,
    ) -> None:
        super().__init__(model, **kwargs)
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY') or ''
        self.base_url = base_url.rstrip('/')
        if not self.api_key:
            raise ValueError(
                'OpenRouter API key not provided. '
                'Set OPENROUTER_API_KEY or pass api_key.'
            )

    async def generate(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> GenerateResult:
        url = f'{self.base_url}/chat/completions'
        payload: Dict[str, Any] = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
        }
        if max_tokens is not None:
            payload['max_tokens'] = max_tokens

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://bantu-os.github.io',
            'X-Title': 'Bantu-OS',
        }

        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()
                text = (
                    data.get('choices', [{}])[0]
                    .get('message', {})
                    .get('content', '')
                )
                return GenerateResult(text=text, raw=data)