"""
LLM Manager - Handles loading and managing language models.
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List

# Provider interfaces
from .providers.base import LLMProvider, ChatMessage, GenerateResult
from .providers.openai_chat import OpenAIChatProvider


class LLMManager:
    """Manages chat LLM providers and active model selection.

    This class abstracts provider instantiation so callers don't depend on
    specific vendor SDKs. Today it supports OpenAI Chat; future providers
    (e.g., local LLaMA) can be added without changing consumers.
    """

    def __init__(self) -> None:
        # Mapping of model_name -> provider instance
        self.models: Dict[str, LLMProvider] = {}
        self.active_model: Optional[str] = None

    def _build_provider(self, provider: str, model: str, **kwargs: Any) -> LLMProvider:
        provider_key = provider.lower()
        if provider_key in {"openai", "openai-chat", "openai_chat"}:
            return OpenAIChatProvider(model=model, **kwargs)
        raise ValueError(f"Unsupported provider: {provider}")

    def load_model(self, model_name: str, provider: str = "openai", **kwargs: Any) -> bool:
        """Instantiate and register a model provider under model_name.

        Example:
            manager.load_model("default", provider="openai", model="gpt-4o")
        """
        instance = self._build_provider(provider=provider, model=kwargs.pop("model", model_name), **kwargs)
        self.models[model_name] = instance
        # If no active model, set this one
        if self.active_model is None:
            self.active_model = model_name
        return True

    def unload_model(self, model_name: str) -> bool:
        """Unload a language model provider by name."""
        if model_name in self.models:
            del self.models[model_name]
            if self.active_model == model_name:
                self.active_model = None
            return True
        return False

    def set_active_model(self, model_name: str) -> bool:
        """Set the active language model by name."""
        if model_name in self.models:
            self.active_model = model_name
            return True
        return False

    def list_models(self) -> List[str]:
        """List available model names in the manager."""
        return list(self.models.keys())

    async def generate(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> GenerateResult:
        """Generate a response using the active model provider."""
        if not self.active_model or self.active_model not in self.models:
            raise RuntimeError("No active model configured in LLMManager.")
        provider = self.models[self.active_model]
        return await provider.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
