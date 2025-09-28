import pytest

from bantu_os.core.kernel.kernel import Kernel
from bantu_os.core.kernel.providers.base import ChatMessage

@pytest.fixture(autouse=True)
def stub_llm_provider(monkeypatch):
    """Stub provider creation to avoid real API and API key requirements.

    Kernel() constructs an LLM via LLMManager._build_provider -> OpenAIChatProvider,
    which raises if no API key is set. We replace it with a dummy provider.
    """
    from bantu_os.core.kernel.llm_manager import LLMManager

    class DummyProvider:
        def __init__(self, model: str, **kwargs):
            self.model = model

        async def generate(self, *, messages, temperature=0.7, max_tokens=None, **kwargs):
            # Default dummy behavior; tests can override kernel.llm.generate if needed
            return {"text": "stub", "raw": {}}

    def _fake_build_provider(self, provider: str, model: str, **kwargs):
        return DummyProvider(model=model, **kwargs)

    monkeypatch.setattr(LLMManager, "_build_provider", _fake_build_provider, raising=True)
    yield


@pytest.mark.asyncio
async def test_generate_response_returns_structured_result(monkeypatch):
    kernel = Kernel()

    captured = {}

    async def fake_generate(*, messages, temperature=0.7, max_tokens=None, **kwargs):
        captured["messages"] = messages
        captured["temperature"] = temperature
        captured["max_tokens"] = max_tokens
        return {"text": "hello", "raw": {"ok": True}}

    # Patch the instance method to avoid real API
    kernel.llm.generate = fake_generate  # type: ignore

    msgs: list[ChatMessage] = [
        {"role": "system", "content": "You are a test bot"},
        {"role": "user", "content": "Say hi"},
    ]

    result = await kernel.generate_response(messages=msgs, temperature=0.2, max_tokens=64)

    assert isinstance(result, dict)
    assert result.get("text") == "hello"
    assert "raw" in result and result["raw"] == {"ok": True}
    # Ensure our inputs were passed through
    assert captured["messages"] == msgs
    assert captured["temperature"] == 0.2
    assert captured["max_tokens"] == 64


@pytest.mark.asyncio
async def test_process_input_builds_messages_basic(monkeypatch):
    kernel = Kernel()

    captured = {}

    async def fake_generate(*, messages, temperature=0.7, max_tokens=None, **kwargs):
        captured["messages"] = messages
        return {"text": "Processed: " + messages[-1]["content"], "raw": {}}

    kernel.llm.generate = fake_generate  # type: ignore

    output = await kernel.process_input(
        text="Hello world",
        system_prompt="System rules",
        temperature=0.1,
    )

    # process_input returns only the text field
    assert output == "Processed: Hello world"

    msgs = captured["messages"]
    assert msgs[0]["role"] == "system" and msgs[0]["content"] == "System rules"
    assert msgs[-1]["role"] == "user" and msgs[-1]["content"] == "Hello world"


@pytest.mark.asyncio
async def test_process_input_with_context(monkeypatch):
    kernel = Kernel()

    captured = {}

    async def fake_generate(*, messages, **kwargs):
        captured["messages"] = messages
        return {"text": "ok", "raw": {}}

    kernel.llm.generate = fake_generate  # type: ignore

    context: list[ChatMessage] = [
        {"role": "user", "content": "Prev Q"},
        {"role": "assistant", "content": "Prev A"},
    ]

    _ = await kernel.process_input(text="New Q", system_prompt=None, context=context)

    msgs = captured["messages"]
    # Expect context preserved then new user message appended
    assert msgs[0] == context[0]
    assert msgs[1] == context[1]
    assert msgs[2]["role"] == "user" and msgs[2]["content"] == "New Q"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prompt",
    [
        "",  # empty
        "a" * 1000,  # long
        "Line1\nLine2\nLine3",  # multiline
        "Special chars !@#$%^&*()_+-=[]{};:'\",.<>/?|`~ and emojis 😀🚀",
    ],
)
async def test_process_input_various_prompts(monkeypatch, prompt):
    kernel = Kernel()

    async def fake_generate(*, messages, **kwargs):
        # Echo back last user content to verify round-trip
        return {"text": messages[-1]["content"], "raw": {}}

    kernel.llm.generate = fake_generate  # type: ignore

    output = await kernel.process_input(text=prompt)
    assert output == prompt


def test_use_tool_success():
    # Register a simple dummy tool
    def echo_tool(value: str, times: int = 1) -> str:
        return " ".join([value] * times)

    kernel = Kernel(tools={"echo": echo_tool})

    result = kernel.use_tool("echo", value="hi", times=3)
    assert result == "hi hi hi"


def test_use_tool_missing_raises():
    kernel = Kernel()
    with pytest.raises(KeyError):
        kernel.use_tool("nonexistent")
