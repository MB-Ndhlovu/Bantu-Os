import asyncio
import json
import os
import types
import pytest

from bantu_os.agents.agent_manager import AgentManager


class MockKernel:
    """Mock Kernel that returns predetermined JSON actions based on input."""

    def __init__(self, plans):
        # plans: dict of user_input -> action dict or raw string
        self.plans = plans

    async def process_input(self, text: str, system_prompt=None, context=None, temperature=0.7, max_tokens=None, **kwargs):
        plan = self.plans.get(text)
        if isinstance(plan, dict):
            return json.dumps(plan)
        return plan or "{\"action\": \"respond\", \"args\": {\"message\": \"ok\"}}"


def test_agent_manager_respond_action():
    plans = {
        "hello": {"thought": "no tool", "action": "respond", "args": {"message": "Hi there"}},
    }
    am = AgentManager(kernel=MockKernel(plans))
    out = asyncio.run(am.execute("hello"))
    assert out == "Hi there"


def test_agent_manager_unknown_tool():
    plans = {
        "do-x": {"thought": "use missing", "action": "missing_tool", "args": {"x": 1}},
    }
    am = AgentManager(kernel=MockKernel(plans))
    out = asyncio.run(am.execute("do-x"))
    assert out.startswith("Unknown tool: missing_tool")


def test_agent_manager_calculator_tool():
    plans = {
        "calc": {"thought": "use calc", "action": "calculator", "args": {"expression": "2 + 2 * 3"}},
    }
    am = AgentManager(kernel=MockKernel(plans))

    from bantu_os.agents.tools import calculate

    am.register_tool("calculator", calculate)
    out = asyncio.run(am.execute("calc"))
    assert out == "8"


def test_agent_manager_filesystem_tool(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello")
    d = tmp_path

    plans = {
        "ls": {"thought": "list dir", "action": "list_dir", "args": {"path": str(d)}},
        "cat": {"thought": "read file", "action": "read_text", "args": {"path": str(f)}},
    }
    am = AgentManager(kernel=MockKernel(plans))

    from bantu_os.agents.tools import list_dir, read_text

    am.register_tool("list_dir", list_dir)
    am.register_tool("read_text", read_text)

    out_ls = asyncio.run(am.execute("ls"))
    assert "a.txt" in out_ls

    out_cat = asyncio.run(am.execute("cat"))
    assert out_cat == "hello"


def test_agent_manager_tool_arg_error():
    plans = {
        "bad": {"thought": "call", "action": "echo", "args": {"unexpected": 1}},
    }
    am = AgentManager(kernel=MockKernel(plans))
    am.register_tool("echo", lambda text: text)

    out = asyncio.run(am.execute("bad"))
    assert out.startswith("Tool 'echo' argument error")


def test_agent_manager_malformed_json_returns_raw_text():
    plans = {
        "weird": "This is not JSON but maybe includes {broken}",
    }
    am = AgentManager(kernel=MockKernel(plans))

    out = asyncio.run(am.execute("weird"))
    assert out == plans["weird"]
