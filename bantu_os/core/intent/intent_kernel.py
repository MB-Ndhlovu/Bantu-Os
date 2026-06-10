from __future__ import annotations

from typing import Any

from bantu_os.agents.agent_manager import AgentManager

from .goal_planner import GoalPlanner
from .goal_tree import GoalNode, GoalStatus, GoalTree
from .intent_renderer import IntentRenderer


class IntentKernel:
    def __init__(
        self,
        agent_manager: Any,
        planner: GoalPlanner | None = None,
        renderer: IntentRenderer | None = None,
    ) -> None:
        self.agent_manager = agent_manager
        self.planner = planner or GoalPlanner(
            llm_manager=getattr(getattr(agent_manager, "kernel", None), "llm", None),
            available_tools=getattr(agent_manager, "tools", {}).keys(),
        )
        self.renderer = renderer or IntentRenderer()

    async def receive(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        tree = await self.planner.decompose(text, context=context or {})
        if tree.clarification_needed:
            return {
                "ok": True,
                "type": "clarification_needed",
                "question": tree.clarification_question or "Could you clarify your goal?",
                "tree": tree.to_dict(),
            }
        executed = await self.execute(tree)
        return {
            "ok": True,
            "type": "goal_complete",
            "summary": self.renderer.render(executed),
            "tree": executed.to_dict(),
        }

    async def execute(self, tree: GoalTree) -> GoalTree:
        for child in tree.root.children:
            await self._walk(child)
        tree.root.mark_done(self.renderer.render(tree))
        return tree

    async def _walk(self, node: GoalNode) -> None:
        node.status = GoalStatus.RUNNING
        if node.children:
            for child in node.children:
                await self._walk(child)
            node.mark_done()
            return

        try:
            result = await self._execute_leaf(node)
            node.mark_done(result)
        except Exception as exc:
            node.mark_failed(str(exc))
            raise

    async def _execute_leaf(self, node: GoalNode) -> str:
        if node.tool and hasattr(self.agent_manager, "_execute_tool_call"):
            outcome = await self.agent_manager._execute_tool_call(node.tool, node.tool_params or {})
            if isinstance(outcome, str):
                return outcome
            if isinstance(outcome, dict):
                if outcome.get("ok") is True and "result" in outcome:
                    return str(outcome["result"])
                raise RuntimeError(str(outcome.get("error", "Tool execution failed")))
        if hasattr(self.agent_manager, "execute"):
            return str(await self.agent_manager.execute(node.text))
        raise RuntimeError("No execution backend configured")
