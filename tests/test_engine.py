"""Unit tests for bantu_os.ai.engine."""

from __future__ import annotations

import pytest

from bantu_os.ai.engine import AIEngine, BUILTIN_HANDLERS
from bantu_os.ai.tools.schema import BUILTIN_TOOLS, Tool, ToolParam


class FakeProvider:
    """Minimal fake LLM provider that returns canned responses."""

    def __init__(self, responses: list[dict]) -> None:
        self._responses = responses
        self._idx = 0

    async def generate(self, messages, temperature=0.7, max_tokens=None, **kwargs):
        if self._idx < len(self._responses):
            r = self._responses[self._idx]
            self._idx += 1
            return r
        return {"text": "fallback", "raw": {}}


class FakeLLMManager:
    def __init__(self, responses: list[dict] | None = None) -> None:
        self._provider = FakeProvider(responses or [{"text": "no-op", "raw": {}}])

    async def generate(self, messages, temperature=0.7, max_tokens=None, **kwargs):
        return await self._provider.generate(
            messages, temperature, max_tokens, **kwargs
        )


# ------------------------------------------------------------------
# Schema tests
# ------------------------------------------------------------------
class TestToolSchema:
    def test_tool_to_function_schema_basic(self):
        t = Tool(
            name="test.read",
            description="Read a test file.",
            params=[
                ToolParam(name="path", description="File path.", type="string"),
            ],
        )
        schema = t.to_function_schema()
        assert schema["name"] == "test.read"
        assert schema["description"] == "Read a test file."
        assert schema["parameters"]["type"] == "object"
        assert "path" in schema["parameters"]["properties"]
        assert "required" in schema["parameters"]

    def test_tool_to_function_schema_with_optional(self):
        t = Tool(
            name="test.list",
            description="List files.",
            params=[
                ToolParam(
                    name="path",
                    description="Directory.",
                    type="string",
                    required=False,
                    default=".",
                ),
            ],
        )
        schema = t.to_function_schema()
        assert "path" in schema["parameters"]["properties"]
        # optional param should not appear in required list
        assert "path" not in schema["parameters"].get("required", [])


# ------------------------------------------------------------------
# Engine construction
# ------------------------------------------------------------------
class TestAIEngineConstruction:
    def test_engine_accepts_llm_manager(self):
        llm = FakeLLMManager()
        engine = AIEngine(llm)
        assert engine.llm is llm
        assert engine.system_prompt == "You are a helpful AI assistant."
        assert len(engine.tools) == len(BUILTIN_TOOLS)

    def test_engine_custom_system_prompt(self):
        llm = FakeLLMManager()
        prompt = "Custom prompt."
        engine = AIEngine(llm, system_prompt=prompt)
        assert engine.system_prompt == prompt

    def test_engine_tool_map_indexed(self):
        llm = FakeLLMManager()
        engine = AIEngine(llm)
        for tool in engine.tools:
            assert engine._tool_map[tool.name] is tool


# ------------------------------------------------------------------
# Built-in handlers
# ------------------------------------------------------------------
class TestBuiltinHandlers:
    def test_read_file(self, tmp_path):
        p = tmp_path / "hello.txt"
        p.write_text("hello world")
        result = BUILTIN_HANDLERS["read_file"](path=str(p))
        assert result == "hello world"

    def test_write_file(self, tmp_path):
        path = str(tmp_path / "out.txt")
        result = BUILTIN_HANDLERS["write_file"](path=path, content="foo bar")
        assert "Wrote" in result
        assert (tmp_path / "out.txt").read_text() == "foo bar"

    def test_list_files(self, tmp_path):
        (tmp_path / "a.txt").touch()
        (tmp_path / "b.txt").touch()
        result = BUILTIN_HANDLERS["list_files"](path=str(tmp_path))
        assert "a.txt" in result
        assert "b.txt" in result

    def test_run_command(self):
        result = BUILTIN_HANDLERS["run_command"](command="echo hello")
        assert result["returncode"] == 0
        assert "hello" in result["stdout"]

    def test_send_message(self):
        result = BUILTIN_HANDLERS["send_message"](recipient="test", body="hi")
        assert result["sent"] is True


# ------------------------------------------------------------------
# Tool dispatch
# ------------------------------------------------------------------
class TestToolDispatch:
    def test_dispatch_unknown_tool(self):
        llm = FakeLLMManager()
        engine = AIEngine(llm)
        result = engine._dispatch_tool("nonexistent.tool", {})
        assert result["success"] is False
        assert "Unknown tool" in result["error"]

    def test_dispatch_read_file_success(self, tmp_path):
        p = tmp_path / "hello.txt"
        p.write_text("hello world")
        llm = FakeLLMManager()
        engine = AIEngine(llm)
        result = engine._dispatch_tool("read_file", {"path": str(p)})
        assert result["success"] is True
        assert result["result"] == "hello world"


# ------------------------------------------------------------------
# Tool call extraction
# ------------------------------------------------------------------
class TestToolCallExtraction:
    def test_extract_from_openai_style_raw(self):
        llm = FakeLLMManager()
        engine = AIEngine(llm)
        raw = {
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": "read_file",
                    "arguments": '{"path": "/etc/hosts"}',
                }
            ]
        }
        calls = engine._extract_tool_calls(raw, "")
        assert len(calls) == 1
        assert calls[0]["name"] == "read_file"
        assert calls[0]["arguments"] == {"path": "/etc/hosts"}

    def test_extract_from_text_code_block(self):
        llm = FakeLLMManager()
        engine = AIEngine(llm)
        text = 'Some text before\n```json\n{"name": "read_file", "arguments": {"path": "/tmp/test"}}\n```\nmore text'
        calls = engine._extract_from_text(text)
        assert len(calls) == 1
        assert calls[0]["name"] == "read_file"

    def test_extract_nested_function_object(self):
        llm = FakeLLMManager()
        engine = AIEngine(llm)
        raw = {
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "write_file",
                        "arguments": '{"path": "/tmp/out", "content": "hi"}',
                    },
                }
            ]
        }
        calls = engine._extract_tool_calls(raw, "")
        assert len(calls) == 1
        assert calls[0]["name"] == "write_file"


# ------------------------------------------------------------------
# Run loop
# ------------------------------------------------------------------
class TestEngineRun:
    @pytest.mark.asyncio
    async def test_run_no_tool_calls_returns_text(self):
        llm = FakeLLMManager(responses=[{"text": "Hello, world.", "raw": {}}])
        engine = AIEngine(llm)
        result = await engine.run("Say hello")
        assert result == "Hello, world."

    @pytest.mark.asyncio
    async def test_run_max_iterations_guard(self):
        # Every response triggers a tool call — should hit max_iterations and return loop message
        def make_response():
            return {
                "text": "Calling tool",
                "raw": {
                    "tool_calls": [
                        {
                            "id": "x",
                            "name": "read_file",
                            "arguments": '{"path": "/tmp/x"}',
                        }
                    ]
                },
            }

        responses = [make_response() for _ in range(20)]
        llm = FakeLLMManager(responses=responses)
        engine = AIEngine(llm, max_iterations=3)
        result = await engine.run("test")
        assert "caught in a loop" in result

    @pytest.mark.asyncio
    async def test_run_memory_context_passed(self):
        captured_messages = []

        class CapturingLLM(FakeLLMManager):
            async def generate(self, messages, **kwargs):
                captured_messages.extend(messages)
                return {"text": "done", "raw": {}}

        llm = CapturingLLM()
        engine = AIEngine(llm)
        await engine.run(
            "test",
            memory_context=[
                {"role": "user", "content": "previous user msg"},
                {"role": "assistant", "content": "previous assistant msg"},
            ],
        )
        # memory_context should appear in messages
        assert any(m.get("content") == "previous user msg" for m in captured_messages)
