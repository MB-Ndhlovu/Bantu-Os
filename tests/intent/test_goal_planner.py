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
