"""
Tests for agents/agent_manager.py — AgentManager, BaseAgent, and agents.
"""

import pytest


class TestAgentToolRegistry:
    """Tool registration on concrete agents."""

    def test_register_tool(self):
        from bantu_os.agents.agent_manager import ShellAgent

        agent = ShellAgent()
        agent.register_tool("add", lambda a, b: a + b)
        assert "add" in agent._tool_registry

    @pytest.mark.asyncio
    async def test_call_tool(self):
        from bantu_os.agents.agent_manager import ShellAgent

        agent = ShellAgent()
        agent.register_tool("add", lambda a, b: a + b)
        result = await agent.call_tool("add", {"a": 2, "b": 3})
        assert result == 5

    @pytest.mark.asyncio
    async def test_call_tool_unknown_raises(self):
        from bantu_os.agents.agent_manager import ShellAgent

        agent = ShellAgent()
        with pytest.raises(ValueError, match="Unknown tool"):
            await agent.call_tool("unknown", {})


class TestShellAgent:
    @pytest.mark.asyncio
    async def test_shell_agent_runs_command(self):
        from bantu_os.agents.agent_manager import ShellAgent

        agent = ShellAgent()
        result = await agent.run("echo hello")
        assert result.success is True
        assert "hello" in result.output


class TestMemoryAgent:
    def test_store_and_retrieve(self):
        from bantu_os.agents.agent_manager import MemoryAgent

        agent = MemoryAgent()
        agent.store("note1", "Python is awesome")
        results = agent.retrieve("Python")
        assert len(results) == 1
        assert results[0]["id"] == "note1"

    def test_retrieve_no_match(self):
        from bantu_os.agents.agent_manager import MemoryAgent

        agent = MemoryAgent()
        agent.store("note1", "Something unrelated")
        results = agent.retrieve("Python")
        assert results == []


class TestAgentManager:
    def test_register_and_list_agents(self):
        from bantu_os.agents.agent_manager import AgentManager, ShellAgent

        mgr = AgentManager()
        mgr.register(ShellAgent())
        assert "shell" in mgr.list_agents()

    @pytest.mark.asyncio
    async def test_dispatch_unknown_agent_raises(self):
        from bantu_os.agents.agent_manager import AgentManager

        mgr = AgentManager()
        with pytest.raises(ValueError, match="Unknown agent"):
            await mgr.dispatch("ghost", "hello")

    def test_send_and_get_messages(self):
        from bantu_os.agents.agent_manager import AgentManager, ShellAgent

        mgr = AgentManager()
        mgr.register(ShellAgent())
        mgr.send_message("shell", "shell", "ping", {"seq": 1})
        msgs = mgr.get_messages("shell")
        assert len(msgs) == 1
        assert msgs[0].type == "ping"

    @pytest.mark.asyncio
    async def test_dispatch_shell_agent(self):
        from bantu_os.agents.agent_manager import AgentManager, ShellAgent

        mgr = AgentManager()
        mgr.register(ShellAgent())
        result = await mgr.dispatch("shell", "echo world")
        assert result.success is True
        assert "world" in result.output
