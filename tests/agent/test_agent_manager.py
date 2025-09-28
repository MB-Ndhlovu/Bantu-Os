import pytest

from bantu_os.agents.agent_manager import AgentManager


@pytest.mark.asyncio
async def test_register_tool_adds_tool(monkeypatch):
    am = AgentManager()

    def dummy():
        return "ok"

    am.register_tool("dummy", dummy)
    assert "dummy" in am.tools
    assert am.tools["dummy"] is dummy


@pytest.mark.asyncio
async def test_execute_routes_to_calculator(monkeypatch):
    # Calculator tool
    def calculator(expression: str) -> int:
        # Very simple and unsafe eval for testing purposes only
        return int(eval(expression))

    am = AgentManager(tools={"calculator": calculator})

    async def fake_process_input(text, system_prompt=None, temperature=None, max_tokens=None, **kwargs):
        return (
            '{"thought": "use calc", "action": "calculator", "args": {"expression": "2+2"}}'
        )

    monkeypatch.setattr(am.kernel, "process_input", fake_process_input)

    out = await am.execute("2+2")
    assert out == "4"
    assert int(out) == 4


@pytest.mark.asyncio
async def test_execute_direct_respond(monkeypatch):
    am = AgentManager()

    async def fake_process_input(text, **kwargs):
        return '{"action": "respond", "args": {"message": "hello"}}'

    monkeypatch.setattr(am.kernel, "process_input", fake_process_input)

    out = await am.execute("hi")
    assert out == "hello"


@pytest.mark.asyncio
async def test_execute_invalid_json_fallback(monkeypatch):
    am = AgentManager()

    async def fake_process_input(text, **kwargs):
        return "this is not json"

    monkeypatch.setattr(am.kernel, "process_input", fake_process_input)

    out = await am.execute("anything")
    # Falls back to returning raw model text
    assert out == "this is not json"


@pytest.mark.asyncio
async def test_execute_unknown_tool(monkeypatch):
    am = AgentManager()

    async def fake_process_input(text, **kwargs):
        return '{"action": "no_such_tool", "args": {}}'

    monkeypatch.setattr(am.kernel, "process_input", fake_process_input)

    out = await am.execute("call unknown")
    assert out == "Unknown tool: no_such_tool"


@pytest.mark.asyncio
async def test_execute_tool_argument_error(monkeypatch):
    # Tool requires parameter 'a'; we will provide 'b' to trigger TypeError
    def needs_a(a: int) -> int:
        return a

    am = AgentManager(tools={"needs_a": needs_a})

    async def fake_process_input(text, **kwargs):
        return '{"action": "needs_a", "args": {"b": 1}}'

    monkeypatch.setattr(am.kernel, "process_input", fake_process_input)

    out = await am.execute("trigger arg error")
    assert out.startswith("Tool 'needs_a' argument error:")


@pytest.mark.asyncio
async def test_execute_tool_exception_caught(monkeypatch):
    def boom() -> str:
        raise RuntimeError("kaboom")

    am = AgentManager(tools={"boom": boom})

    async def fake_process_input(text, **kwargs):
        return '{"action": "boom", "args": {}}'

    monkeypatch.setattr(am.kernel, "process_input", fake_process_input)

    out = await am.execute("explode")
    assert out.startswith("Tool 'boom' failed:")
