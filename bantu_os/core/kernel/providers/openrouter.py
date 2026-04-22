"""
OpenRouter provider implementation using aiohttp.

OpenRouter provides unified access to many LLM providers (Anthropic, Meta, Google, etc.)
via an OpenAI-compatible API.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import aiohttp

from .base import LLMProvider, ChatMessage, GenerateResult


class OpenRouterProvider(LLMProvider):
    """OpenRouter Chat Completions API provider.

    Environment:
    - OPENROUTER_API_KEY or explicit api_key in config
    - OPENROUTER_BASE_URL optional override (default https://openrouter.ai/api/v1)

    Supported models include:
    - anthropic/claude-3.5-sonnet, anthropic/claude-3-opus
    - meta-llama/llama-3-70b-instruct
    - google/gemini-pro-1.5
    - and many more via OpenRouter catalog
    """

    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, model: str, **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        self.api_key: str = (
            kwargs.get("api_key") or os.getenv("OPENROUTER_API_KEY") or ""
        )
        self.base_url: str = kwargs.get("base_url") or os.getenv(
            "OPENROUTER_BASE_URL", self.DEFAULT_BASE_URL
        )
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key not provided. Set OPENROUTER_API_KEY or pass api_key."
            )

    async def generate(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> GenerateResult:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
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
            "HTTP-Referer": "https://bantu-os.local",
            "X-Title": "Bantu OS",
        }

        timeout = aiohttp.ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()
                text = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                return GenerateResult(text=text, raw=data)
