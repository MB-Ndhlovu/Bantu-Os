"""
Kernel wrapper for Bantu OS.

Provides a modular interface around an underlying chat LLM and optional tools.
The Kernel is intentionally lightweight and depends only on the internal
LLMManager (which itself uses pluggable providers like OpenAI, and later LLaMA).

Public methods:
- process_input(text, system_prompt=None, context=None, **gen_kwargs)
- generate_response(messages, **gen_kwargs)
- use_tool(name, **kwargs)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable

from .llm_manager import LLMManager
from .providers.base import ChatMessage, GenerateResult
from ...config import settings
from ...memory import Memory, EmbeddingsProvider, OpenAIEmbeddingsProvider


class Kernel:
    """High-level orchestrator around the active LLM and tool registry.

    This class hides provider-specific details and exposes a clean surface
    for prompting and tool use. Swap providers via LLMManager without
    changing Kernel consumers.
    """

    def __init__(
        self,
        model_name: str = "default",
        provider: str = "openai",
        provider_model: Optional[str] = None,
        api_key: Optional[str] = None,
        tools: Optional[Dict[str, Callable[..., Any]]] = None,
        # Optional memory integration
        memory: Optional[Memory] = None,
        memory_embeddings_provider: Optional[EmbeddingsProvider] = None,
        memory_top_k: int = 3,
    ) -> None:
        self.llm = LLMManager()

        # Derive provider model and API key from settings if not provided
        resolved_model = provider_model or settings.DEFAULT_LLM_MODEL
        resolved_api_key = api_key or settings.LLM_API_KEY

        # Load provider instance under model_name key
        self.llm.load_model(
            model_name,
            provider=provider,
            model=resolved_model,
            api_key=resolved_api_key,
        )
        self.llm.set_active_model(model_name)

        # Simple tool registry: name -> callable
        self.tools: Dict[str, Callable[..., Any]] = tools or {}

        # Optional Memory integration (kept disabled unless configured)
        self.memory: Optional[Memory] = memory
        self.memory_top_k = memory_top_k
        if self.memory and memory_embeddings_provider is not None:
            self.memory.set_embeddings_provider(memory_embeddings_provider)
        # If a Memory instance was provided but no embeddings assigned, try OpenAI if key exists
        if self.memory and self.memory.embeddings is None and (api_key or settings.LLM_API_KEY):
            try:
                provider = OpenAIEmbeddingsProvider(api_key=api_key or settings.LLM_API_KEY)
                self.memory.set_embeddings_provider(provider)
            except Exception:
                # Silently skip if embedding provider cannot be initialized
                pass

    def register_tool(self, name: str, fn: Callable[..., Any]) -> None:
        """Register a callable tool that Kernel can invoke by name."""
        self.tools[name] = fn

    async def process_input(
        self,
        text: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[ChatMessage]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Convenience method: build messages from raw text and generate.

        - text: the user's input string
        - system_prompt: optional system instruction for the model
        - context: optional prior messages in ChatMessage format
        Returns model text output.
        """
        messages: List[ChatMessage] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            messages.extend(context)

        # Retrieve relevant memory (if configured) and inject as an additional system message
        if self.memory and self.memory.embeddings is not None:
            try:
                results = await self.memory.retrieve_memory(query=text, top_k=self.memory_top_k)
                if results:
                    mem_snippets = []
                    for r in results:
                        snippet = r.get("text") or ""
                        if snippet:
                            mem_snippets.append(f"- {snippet}")
                    if mem_snippets:
                        mem_block = "\n".join(mem_snippets)
                        messages.append({
                            "role": "system",
                            "content": f"Relevant memory items (most similar first):\n{mem_block}",
                        })
            except Exception:
                # If memory retrieval fails, continue without it
                pass

        messages.append({"role": "user", "content": text})

        result = await self.llm.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        output_text = result.get("text", "")

        # Store interaction to memory (if configured)
        if self.memory and self.memory.embeddings is not None:
            try:
                await self.memory.store_text(text)
                if output_text:
                    await self.memory.store_text(output_text)
            except Exception:
                # Ignore memory store failures
                pass

        return output_text

    async def generate_response(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> GenerateResult:
        """Low-level method: pass chat messages directly to the model."""
        return await self.llm.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    def use_tool(self, name: str, /, **kwargs: Any) -> Any:
        """Invoke a registered tool by name with keyword arguments.

        Tools are plain Python callables. You can register async tools as well,
        but this method does not await them by design—keep the interface simple.
        If you need async tooling, either call it directly or add an async
        variant method.
        """
        if name not in self.tools:
            raise KeyError(f"Tool not found: {name}")
        return self.tools[name](**kwargs)
