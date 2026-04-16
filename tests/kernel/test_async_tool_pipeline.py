"""
Tests for async tool execution pipeline in Kernel.

Covers:
- use_tool works for both sync and async callables
- process_input accepts an optional async tool loop
- Tool result injection back into messages
- Error handling for tool failures
"""
import pytest
from unittest.mock import AsyncMock

from bantu_os.core.kernel.kernel import Kernel
from bantu_os.core.kernel.providers.base import ChatMessage


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def echo_sync(value: str, times: int = 1) -> str:
    """Sync echo tool."""
    return " ".join([value] * times)


async def echo_async(value: str, times: int = 1) -> str:
    """Async echo tool."""
    return " ".join([value] * times)


async def flaky_async(value: str) -> str:
    """Async tool that raises."""
    raise RuntimeError("flaky failure")


# ------------------------------------------------------------------
# use_tool: sync tools
# ------------------------------------------------------------------

def test_use_tool_sync_success():
    kernel = Kernel(tools={"echo": echo_sync})
    result = kernel.use_tool("echo", value="hello", times=2)
    assert result == "hello hello"


def test_use_tool_sync_missing_raises():
    kernel = Kernel()
    with pytest.raises(KeyError, match="nonexistent"):
        kernel.use_tool("nonexistent")


# ------------------------------------------------------------------
# use_tool: async tools (via the sync wrapper)
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_use_tool_async_via_sync_interface():
    """Async tools registered via Kernel(tools={...}) are still callable
    through the sync use_tool().  The caller is responsible for awaiting
    if the callable is coroutine.
    """
    kernel = Kernel(tools={"echo_a": echo_async})
    # use_tool is sync — calling an async function returns a coroutine
    result = kernel.use_tool("echo_a", value="hi", times=3)
    # result is a coroutine, not the resolved value
    assert hasattr(result, "__await__")
    resolved = await result
    assert resolved == "hi hi hi"


# ------------------------------------------------------------------
# Async tool pipeline on process_input via run_tools hook
# ------------------------------------------------------------------

TOOL_CALL_RE = __import__("re")


def parse_tool_calls(text: str):
    """Minimal parser that extracts tool calls from plain-text LLM output.
    Looks for lines like:  [TOOL_CALL] name:calc args:{"x":1}[/TOOL_CALL]
    Returns list of dicts with name and args.
    """
    pattern = r"\[TOOL_CALL\]\s*(\w+)\s+args:(\{[^}]*\})\s*\[/TOOL_CALL\]"
    results = []
    for m in TOOL_CALL_RE.finditer(pattern, text):
        import json
        name, args_json = m.groups()
        try:
            args = json.loads(args_json)
        except Exception:
            args = {}
        results.append({"name": name, "args": args})
    return results


async def run_tools_sync(kernel: Kernel, calls, max_iterations=5):
    """Execute tool calls synchronously using kernel.use_tool.
    Returns list of (tool_name, result) tuples.
    """
    results = []
    for call in calls:
        try:
            result = kernel.use_tool(call["name"], **call["args"])
            results.append((call["name"], result))
        except Exception as exc:
            results.append((call["name"], {"error": str(exc)}))
    return results


async def run_tools_async(kernel: Kernel, calls, max_iterations=5):
    """Execute tool calls asynchronously, awaiting coroutines automatically.
    Returns list of (tool_name, result) tuples.
    """
    outcomes = []
    for call in calls:
        try:
            raw = kernel.use_tool(call["name"], **call["args"])
            result = await raw if hasattr(raw, "__await__") else raw
            outcomes.append((call["name"], result))
        except Exception as exc:
            outcomes.append((call["name"], {"error": str(exc)}))
    return outcomes


# ------------------------------------------------------------------
# Tool call detection + execution pipeline (mocked LLM)
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_async_tool_execution_pipeline_basic():
    """Kernel with an async tool is invoked; pipeline resolves coroutines."""
    kernel = Kernel(tools={"echo_a": echo_async})

    tool_calls = [{"name": "echo_a", "args": {"value": "from pipeline", "times": 2}}]
    outcomes = await run_tools_async(kernel, tool_calls)

    assert len(outcomes) == 1
    name, result = outcomes[0]
    assert name == "echo_a"
    assert result == "from pipeline from pipeline"


@pytest.mark.asyncio
async def test_async_tool_execution_pipeline_error_handling():
    """Tool failures are captured with error dict, not raised."""
    kernel = Kernel(tools={"flaky": flaky_async})

    tool_calls = [{"name": "flaky", "args": {"value": "oops"}}]
    outcomes = await run_tools_async(kernel, tool_calls)

    assert len(outcomes) == 1
    name, result = outcomes[0]
    assert name == "flaky"
    assert isinstance(result, dict)
    assert "error" in result
    assert "flaky failure" in result["error"]


@pytest.mark.asyncio
async def test_process_input_with_async_tool_roundtrip(monkeypatch):
    """process_input flow with a simulated tool-call → resolve → continue loop.

    Simulates:
    1. LLM called with user input
    2. LLM outputs a tool call request
    3. Kernel executes the tool asynchronously
    4. Kernel feeds result back into a second LLM call
    5. Final response is returned
    """
    kernel = Kernel(tools={"echo_a": echo_async})

    call_count = [0]

    async def fake_llm_generate(*, messages, **kwargs):
        call_count[0] += 1
        content = messages[-1]["content"]

        if call_count[0] == 1:
            # First turn: model requests a tool
            return {
                "text": "[TOOL_CALL] echo_a args:{\"value\":\"ping\",\"times\":3} [/TOOL_CALL]",
                "raw": {},
            }
        else:
            # Second turn: model consumes tool result and responds
            assert "tool_result" in content.lower() or "ping ping ping" in content
            return {"text": "pong", "raw": {}}

    kernel.llm.generate = fake_llm_generate  # type: ignore

    # First call - triggers tool detection
    output1 = await kernel.process_input(text="Run echo_a with ping")
    # LLM asked for a tool call, so output contains the tool request text
    assert "[TOOL_CALL]" in output1

    # Simulate what an agent would do: detect tool calls, execute, re-prompt
    calls = parse_tool_calls(output1)
    assert len(calls) == 1
    assert calls[0]["name"] == "echo_a"

    outcomes = await run_tools_async(kernel, calls)
    tool_result = outcomes[0][1]

    # Feed result back to model
    result_msg = f"Tool result: {tool_result}"
    final_output = await kernel.process_input(text=result_msg)
    assert final_output == "pong"


@pytest.mark.asyncio
async def test_async_pipeline_multiple_tools():
    """Multiple tool calls in a single iteration are all resolved."""
    kernel = Kernel(tools={"echo_a": echo_async, "echo_s": echo_sync})

    tool_calls = [
        {"name": "echo_a", "args": {"value": "async_val", "times": 1}},
        {"name": "echo_s", "args": {"value": "sync_val", "times": 2}},
    ]
    outcomes = await run_tools_async(kernel, tool_calls)

    assert len(outcomes) == 2
    assert outcomes[0] == ("echo_a", "async_val")
    assert outcomes[1] == ("echo_s", "sync_val sync_val")


@pytest.mark.asyncio
async def test_async_pipeline_unknown_tool(monkeypatch):
    """Unknown tool name raises KeyError, captured as error result."""
    kernel = Kernel(tools={"known": echo_sync})

    tool_calls = [{"name": "unknown_tool", "args": {}}]
    outcomes = await run_tools_async(kernel, tool_calls)

    assert len(outcomes) == 1
    name, result = outcomes[0]
    assert name == "unknown_tool"
    assert isinstance(result, dict)
    assert "error" in result