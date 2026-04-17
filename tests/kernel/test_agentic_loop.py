import pytest

from bantu_os.core.kernel.kernel import Kernel


class DummyProvider:
    def __init__(self, model: str, **kwargs):
        self.model = model

    async def generate(self, *, messages, temperature=0.7, max_tokens=None, **kwargs):
        return {}


@pytest.fixture(autouse=True)
def stub_llm_provider(monkeypatch):
    from bantu_os.core.kernel.llm_manager import LLMManager

    def _fake_build_provider(self, provider: str, model: str, **kwargs):
        return DummyProvider(model=model, **kwargs)

    monkeypatch.setattr(LLMManager, '_build_provider', _fake_build_provider, raising=True)


# ------------------------------------------------------------------
# _parse_tool_calls tests
# ------------------------------------------------------------------

class TestParseToolCalls:
    def _parse(self, text):
        return Kernel._parse_tool_calls(text)

    def test_single_tool_call_with_args(self):
        text = r'[TOOL_CALL] echo args:{"value":"ping","times":3} [/TOOL_CALL]'
        calls = self._parse(text)
        assert len(calls) == 1
        assert calls[0] == {'name': 'echo', 'args': {'value': 'ping', 'times': 3}}

    def test_multiple_tool_calls(self):
        text = (
            r'[TOOL_CALL] echo args:{"value":"a"} [/TOOL_CALL] '
            r'[TOOL_CALL] cat args:{"path":"/etc/hostname"} [/TOOL_CALL]'
        )
        calls = self._parse(text)
        assert len(calls) == 2
        assert calls[0] == {'name': 'echo', 'args': {'value': 'a'}}
        assert calls[1] == {'name': 'cat', 'args': {'path': '/etc/hostname'}}

    def test_tool_call_no_args(self):
        text = '[TOOL_CALL] ps args:{} [/TOOL_CALL]'
        calls = self._parse(text)
        assert len(calls) == 1
        assert calls[0] == {'name': 'ps', 'args': {}}

    def test_no_tool_calls_returns_empty(self):
        text = 'Hello, how can I help you today?'
        assert self._parse(text) == []

    def test_invalid_json_returns_empty_args(self):
        text = '[TOOL_CALL] bad args:{not json} [/TOOL_CALL]'
        calls = self._parse(text)
        assert len(calls) == 1
        assert calls[0]['name'] == 'bad'
        assert calls[0]['args'] == {}


# ------------------------------------------------------------------
# agentic_loop tests
# ------------------------------------------------------------------

def echo_tool(value: str, times: int = 1) -> str:
    return ' '.join([value] * times)


@pytest.mark.asyncio
async def test_agentic_loop_no_tool_calls_returns_directly(monkeypatch):
    kernel = Kernel(tools={'echo': echo_tool})
    call_count = [0]

    async def fake_generate(*, messages, **kwargs):
        call_count[0] += 1
        # No tool call in output
        return {'text': 'Final response without any tools', 'raw': {}}

    kernel.llm.generate = fake_generate  # type: ignore

    result = await kernel.agentic_loop(text='Say hello')
    assert result == 'Final response without any tools'
    assert call_count[0] == 1


@pytest.mark.asyncio
async def test_agentic_loop_single_tool_call(monkeypatch):
    kernel = Kernel(tools={'echo': echo_tool})
    call_count = [0]

    async def fake_generate(*, messages, **kwargs):
        call_count[0] += 1
        content = messages[-1]['content']

        if call_count[0] == 1:
            return {'text': r'[TOOL_CALL] echo args:{"value":"ping","times":2} [/TOOL_CALL]', 'raw': {}}
        else:
            # Second call should have tool results injected
            assert 'Tool results:' in content
            assert 'ping ping' in content
            return {'text': 'Got your result: ping ping', 'raw': {}}

    kernel.llm.generate = fake_generate  # type: ignore

    result = await kernel.agentic_loop(text='Run echo with ping')
    assert result == 'Got your result: ping ping'
    assert call_count[0] == 2


@pytest.mark.asyncio
async def test_agentic_loop_multiple_tools_in_sequence(monkeypatch):
    kernel = Kernel(tools={'echo': echo_tool})
    call_count = [0]

    async def fake_generate(*, messages, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {'text': '[TOOL_CALL] echo args:{\\\"value\\\":\\\"a\\\"} [/TOOL_CALL]', 'raw': {}}
        else:
            return {'text': 'Done', 'raw': {}}

    kernel.llm.generate = fake_generate  # type: ignore

    result = await kernel.agentic_loop(text='test')
    assert result == 'Done'
    assert call_count[0] == 2


@pytest.mark.asyncio
async def test_agentic_loop_max_iterations_guards_against_infinite_loop(monkeypatch):
    kernel = Kernel(tools={'echo': echo_tool})
    call_count = [0]

    async def fake_generate(*, messages, **kwargs):
        call_count[0] += 1
        # LLM keeps asking for the same tool every time
        return {'text': '[TOOL_CALL] echo args:{\\\"value\\\":\\\"loop\\\"} [/TOOL_CALL]', 'raw': {}}

    kernel.llm.generate = fake_generate  # type: ignore

    result = await kernel.agentic_loop(text='loop forever', max_iterations=3)
    # Should stop after 3 iterations and return last output
    assert result == '[TOOL_CALL] echo args:{\\\"value\\\":\\\"loop\\\"} [/TOOL_CALL]'
    assert call_count[0] == 3


@pytest.mark.asyncio
async def test_agentic_loop_unknown_tool_returns_error(monkeypatch):
    kernel = Kernel(tools={'echo': echo_tool})
    call_count = [0]

    async def fake_generate(*, messages, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {'text': '[TOOL_CALL] unknown_tool args:{} [/TOOL_CALL]', 'raw': {}}
        else:
            # Tool result should contain error
            content = messages[-1]['content']
            assert 'Tool not found: unknown_tool' in content
            return {'text': f'Saw error: {content}', 'raw': {}}

    kernel.llm.generate = fake_generate  # type: ignore

    result = await kernel.agentic_loop(text='call unknown tool')
    assert 'Saw error' in result
    assert call_count[0] == 2


@pytest.mark.asyncio
async def test_agentic_loop_system_prompt_preserved(monkeypatch):
    kernel = Kernel(tools={'echo': echo_tool})

    async def fake_generate(*, messages, **kwargs):
        # System prompt should be first message
        assert messages[0]['role'] == 'system'
        assert messages[0]['content'] == 'You are a helpful assistant.'
        return {'text': 'hi', 'raw': {}}

    kernel.llm.generate = fake_generate  # type: ignore

    await kernel.agentic_loop(
        text='hello',
        system_prompt='You are a helpful assistant.'
    )


@pytest.mark.asyncio
async def test_agentic_loop_chain_multiple_tools(monkeypatch):
    async def echo_a(value: str, times: int = 1) -> str:
        return ' '.join([value] * times)

    kernel = Kernel(tools={'echo_a': echo_a})
    calls_made = []

    async def fake_generate(*, messages, **kwargs):
        content = messages[-1]['content']
        # First call: LLM requests tool
        if not calls_made:
            calls_made.append(1)
            return {'text': '[TOOL_CALL] echo_a args:{\\\"value\\\":\\\"hello\\\",\\\"times\\\":2} [/TOOL_CALL]', 'raw': {}}
        # Second: tool result injected, LLM responds
        assert 'Tool results:' in content
        return {'text': f'Result received: hello hello', 'raw': {}}

    kernel.llm.generate = fake_generate  # type: ignore

    result = await kernel.agentic_loop(text='run echo_a')
    assert result == 'Result received: hello hello'