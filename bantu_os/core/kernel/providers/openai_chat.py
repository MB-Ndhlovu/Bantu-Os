"""
OpenAI chat provider implementation using aiohttp.

This keeps a minimal dependency footprint and a narrow interface.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import aiohttp

from .base import LLMProvider, ChatMessage, GenerateResult


class OpenAIChatProvider(LLMProvider):
    """OpenAI Chat Completions API provider.

    Environment:
    - OPENAI_API_KEY or explicit api_key in config
    - OPENAI_BASE_URL optional override (default https://api.openai.com)
    """

    def __init__(self, model: str, **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        self.api_key: str = (
            kwargs.get("api_key")
            or os.getenv("OPENAI_API_KEY")
            or ""
        )
        self.base_url: str = kwargs.get("base_url") or os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY or pass api_key.")

    async def generate(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> GenerateResult:
        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()
                text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return GenerateResult(text=text, raw=data)
