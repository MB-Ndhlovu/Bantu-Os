import pytest

from bantu_os.agents.agent_manager import AgentManager
from bantu_os.core.intent.goal_tree import GoalNode, GoalTree
from bantu_os.core.intent.intent_kernel import IntentKernel


class StubPlanner:
    async def decompose(self, text, context=None):
        root = GoalNode(text=text, level=0)
        root.add_child(GoalNode(text="do work", level=1, tool="echo", tool_params={"value": "ok"}))
        return GoalTree(root=root)


@pytest.mark.asyncio
async def test_intent_kernel_executes_goal_tree():
    agent = AgentManager()
    agent.register_tool("echo", lambda value: value)
    kernel = IntentKernel(agent_manager=agent, planner=StubPlanner())
    result = await kernel.receive("deploy project")
    assert result["type"] == "goal_complete"
    assert "deploy project" in result["summary"]


@pytest.mark.asyncio
async def test_intent_kernel_uses_direct_agent_fallback():
    class FallbackAgent(AgentManager):
        async def _execute_tool_call(self, tool_name, args):
            return f"{tool_name}:{args['value']}"

    agent = FallbackAgent()
    kernel = IntentKernel(agent_manager=agent, planner=StubPlanner())
    result = await kernel.receive("deploy project")
    assert result["type"] == "goal_complete"


@pytest.mark.asyncio
async def test_intent_kernel_clarification_path():
    class ClarifyPlanner:
        async def decompose(self, text, context=None):
            root = GoalNode(text=text, level=0)
            return GoalTree(root=root, clarification_needed=True, clarification_question="Which one?")

    agent = AgentManager()
    kernel = IntentKernel(agent_manager=agent, planner=ClarifyPlanner())
    result = await kernel.receive("deploy project")
    assert result["type"] == "clarification_needed"
    assert result["question"] == "Which one?"
