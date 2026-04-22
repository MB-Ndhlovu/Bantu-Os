import pytest

from bantu_os.agents.agent_manager import AgentManager


class FakeKernel:
    """Minimal kernel mock for testing."""

    def __init__(self, response):
        self.response = response

    async def process_input(
        self, text, system_prompt=None, temperature=None, max_tokens=None, **kwargs
    ):
        return self.response


class TestAgentManager:
    """Tests for the AgentManager tool-execution API."""

    # -------------------------------------------------------------------------
    # Tool registration
    # -------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_register_tool_adds_tool(self):
        am = AgentManager()

        def dummy():
            return "ok"

        am.register_tool("dummy", dummy)
        assert "dummy" in am.tools
        assert am.tools["dummy"] is dummy

    # -------------------------------------------------------------------------
    # execute() routing
    # -------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_execute_routes_to_calculator(self):
        def calculator(expression: str) -> str:
            return str(int(eval(expression)))  # safe in test only

        kernel = FakeKernel(
            '{"thought": "use calc", "action": "calculator", "args": {"expression": "2+2"}}'
        )
        am = AgentManager(kernel=kernel)
        am.register_tool("calculator", calculator)

        out = await am.execute("2+2")
        assert out == "4"
        assert int(out) == 4

    @pytest.mark.asyncio
    async def test_execute_direct_respond(self):
        kernel = FakeKernel('{"action": "respond", "args": {"message": "hello"}}')
        am = AgentManager(kernel=kernel)

        out = await am.execute("hi")
        assert out == "hello"

    @pytest.mark.asyncio
    async def test_execute_invalid_json_fallback(self):
        kernel = FakeKernel("this is not json")
        am = AgentManager(kernel=kernel)

        out = await am.execute("anything")
        assert out == "this is not json"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        kernel = FakeKernel('{"action": "no_such_tool", "args": {}}')
        am = AgentManager(kernel=kernel)

        out = await am.execute("call unknown")
        assert out == "Unknown tool: no_such_tool"

    @pytest.mark.asyncio
    async def test_execute_tool_argument_error(self):
        def needs_a(a: int) -> int:
            return a

        kernel = FakeKernel('{"action": "needs_a", "args": {"b": 1}}')
        am = AgentManager(kernel=kernel)
        am.register_tool("needs_a", needs_a)

        out = await am.execute("trigger arg error")
        assert out.startswith("Tool 'needs_a' argument error:")

    @pytest.mark.asyncio
    async def test_execute_tool_exception_caught(self):
        def boom() -> str:
            raise RuntimeError("kaboom")

        kernel = FakeKernel('{"action": "boom", "args": {}}')
        am = AgentManager(kernel=kernel)
        am.register_tool("boom", boom)

        out = await am.execute("explode")
        assert out.startswith("Tool 'boom' failed:")

    # -------------------------------------------------------------------------
    # No-kernel fallback
    # -------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_execute_no_kernel_returns_error_message(self):
        am = AgentManager()  # no kernel
        out = await am.execute("anything")
        assert "no kernel" in out.lower()
