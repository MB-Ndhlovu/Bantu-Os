"""
Base provider interfaces for LLM backends.

This defines a minimal, swappable contract so you can plug in different
providers (e.g., OpenAI, local LLaMA, etc.) without changing Kernel code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypedDict


class ChatMessage(TypedDict, total=False):
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: str


class GenerateResult(TypedDict, total=False):
    text: str
    raw: Any


class LLMProvider(ABC):
    """Abstract interface for a chat-capable LLM provider."""

    def __init__(self, model: str, **kwargs: Any) -> None:
        self.model = model
        self.config: Dict[str, Any] = kwargs

    @abstractmethod
    async def generate(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> GenerateResult:
        """Generate a response from the model given chat messages."""
        raise NotImplementedError
