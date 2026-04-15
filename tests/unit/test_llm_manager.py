"""
Tests for llm_manager — model loading, switching, and generation.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from bantu_os.core.kernel.llm_manager import LLMManager


class TestLLMManager:
    """Unit tests for LLMManager."""

    @pytest.fixture
    def mgr(self) -> LLMManager:
        return LLMManager()

    def test_initial_state(self, mgr: LLMManager) -> None:
        assert mgr.models == {}
        assert mgr.active_model is None

    def test_load_model_sets_active(self, mgr: LLMManager) -> None:
        with patch("bantu_os.core.kernel.llm_manager.OpenAIChatProvider") as mock_provider:
            instance = MagicMock()
            mock_provider.return_value = instance
            result = mgr.load_model("default", provider="openai", model="gpt-4o")
            assert result is True
            assert "default" in mgr.models
            assert mgr.active_model == "default"

    def test_load_multiple_models_keeps_first_active(self, mgr: LLMManager) -> None:
        with patch("bantu_os.core.kernel.llm_manager.OpenAIChatProvider") as mock_provider:
            mock_provider.return_value = MagicMock()
            mgr.load_model("model_a", provider="openai", model="gpt-4o")
            mgr.load_model("model_b", provider="openai", model="gpt-4o-mini")
            assert mgr.active_model == "model_a"

    def test_set_active_model_valid(self, mgr: LLMManager) -> None:
        with patch("bantu_os.core.kernel.llm_manager.OpenAIChatProvider") as mock_provider:
            mock_provider.return_value = MagicMock()
            mgr.load_model("model_a", provider="openai", model="gpt-4o")
            mgr.load_model("model_b", provider="openai", model="gpt-4o-mini")
            result = mgr.set_active_model("model_b")
            assert result is True
            assert mgr.active_model == "model_b"

    def test_set_active_model_invalid(self, mgr: LLMManager) -> None:
        result = mgr.set_active_model("nonexistent")
        assert result is False

    def test_unload_model(self, mgr: LLMManager) -> None:
        with patch("bantu_os.core.kernel.llm_manager.OpenAIChatProvider") as mock_provider:
            mock_provider.return_value = MagicMock()
            mgr.load_model("default", provider="openai", model="gpt-4o")
            result = mgr.unload_model("default")
            assert result is True
            assert "default" not in mgr.models
            assert mgr.active_model is None

    def test_unload_model_clears_active_if_unloaded(self, mgr: LLMManager) -> None:
        with patch("bantu_os.core.kernel.llm_manager.OpenAIChatProvider") as mock_provider:
            mock_provider.return_value = MagicMock()
            mgr.load_model("default", provider="openai", model="gpt-4o")
            mgr.unload_model("default")
            assert mgr.active_model is None

    def test_list_models(self, mgr: LLMManager) -> None:
        with patch("bantu_os.core.kernel.llm_manager.OpenAIChatProvider") as mock_provider:
            mock_provider.return_value = MagicMock()
            mgr.load_model("model_a", provider="openai", model="gpt-4o")
            mgr.load_model("model_b", provider="openai", model="gpt-4o-mini")
            models = mgr.list_models()
            assert set(models) == {"model_a", "model_b"}

    def test_unsupported_provider_raises(self, mgr: LLMManager) -> None:
        with patch.object(mgr, "_build_provider") as mock_build:
            mock_build.side_effect = ValueError("Unsupported provider: anthropic")
            with pytest.raises(ValueError, match="Unsupported provider"):
                mgr.load_model("test", provider="anthropic", model="claude-3")

    @pytest.mark.asyncio
    async def test_generate_no_active_model_raises(self, mgr: LLMManager) -> None:
        with pytest.raises(RuntimeError, match="No active model"):
            await mgr.generate(messages=[])

    @pytest.mark.asyncio
    async def test_generate_calls_provider(self, mgr: LLMManager) -> None:
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value={"text": "hello"})
        mgr.models["default"] = mock_provider
        mgr.active_model = "default"
        result = await mgr.generate(messages=[{"role": "user", "content": "hi"}])
        assert result["text"] == "hello"