"""
OpenAI embeddings provider using aiohttp.

Defaults to text-embedding-3-small for low cost. API key is taken from
OPENAI_API_KEY or provided explicitly.
"""
from __future__ import annotations

import os
from typing import List

import aiohttp
import numpy as np

from .base import EmbeddingsProvider


class OpenAIEmbeddingsProvider(EmbeddingsProvider):
    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None, base_url: str | None = None) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or ""
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com").rstrip("/")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY or pass api_key.")

    async def embed(self, texts: List[str]) -> np.ndarray:
        url = f"{self.base_url}/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
        }
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()
        vectors = [item["embedding"] for item in data.get("data", [])]
        return np.array(vectors, dtype=np.float32)
