import pytest

from bantu_os.core.intent.goal_planner import GoalPlanner


class DummyLLM:
    async def generate(self, *, messages, temperature=0.2):
        return {"text": '{"root_goal":"deploy","steps":[{"id":"1","text":"test","tool":"process","params":{},"requires":[],"destructive":false,"children":[]}]}' }


@pytest.mark.asyncio
async def test_goal_planner_builds_tree():
    planner = GoalPlanner(llm_manager=DummyLLM(), available_tools=["process"])
    tree = await planner.decompose("deploy")
    assert tree.root_goal == "deploy"
    assert tree.root.children[0].text == "test"


@pytest.mark.asyncio
async def test_goal_planner_validation_rejects_unknown_tool():
    planner = GoalPlanner(llm_manager=DummyLLM(), available_tools=["file"])
    with pytest.raises(ValueError):
        await planner.decompose("deploy")


@pytest.mark.asyncio
async def test_goal_planner_can_return_clarification():
    class ClarifyLLM:
        async def generate(self, *, messages, temperature=0.2):
            return {"text": '{"root_goal":"deploy","steps":[],"clarification_needed":true,"clarification_question":"Which project should I deploy?"}' }

    planner = GoalPlanner(llm_manager=ClarifyLLM(), available_tools=[])
    tree = await planner.decompose("deploy")
    assert tree.clarification_needed is True
    assert tree.clarification_question == "Which project should I deploy?"
