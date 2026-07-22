from __future__ import annotations

import json
from typing import Any, Iterable, Optional

from pydantic import BaseModel, Field, ValidationError

from .goal_tree import GoalNode, GoalStatus, GoalTree


class PlannedGoalNode(BaseModel):
    id: str
    text: str
    tool: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict)
    requires: list[str] = Field(default_factory=list)
    destructive: bool = False
    children: list["PlannedGoalNode"] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class PlannedGoalPlan(BaseModel):
    root_goal: str
    steps: list[PlannedGoalNode] = Field(default_factory=list)
    clarification_needed: bool = False
    clarification_question: Optional[str] = None

    class Config:
        extra = "forbid"


PlannedGoalNode.update_forward_refs()


class GoalPlanner:
    def __init__(
        self,
        llm_manager: Any | None = None,
        available_tools: Iterable[str] | None = None,
        memory: Any | None = None,
        memory_top_k: int = 3,
        max_leaf_nodes: int = 12,
        max_nesting: int = 3,
    ) -> None:
        self.llm_manager = llm_manager
        self.available_tools = set(available_tools or [])
        self.memory = memory
        self.memory_top_k = memory_top_k
        self.max_leaf_nodes = max_leaf_nodes
        self.max_nesting = max_nesting

    async def _build_messages(
        self,
        goal_text: str,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        schema = {
            "root_goal": "string",
            "steps": [
                {
                    "id": "string",
                    "text": "string",
                    "tool": "string | null",
                    "params": {},
                    "requires": ["string"],
                    "destructive": False,
                    "children": [],
                }
            ],
        }
        system = (
            "You are GoalPlanner for Bantu-OS. Convert the user's goal into strict JSON only. "
            f"Do not exceed {self.max_leaf_nodes} leaf nodes or {self.max_nesting} levels of nesting. "
            "Return only valid JSON matching this schema: "
            f"{json.dumps(schema)}"
        )
        messages = [{"role": "system", "content": system}]

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Execution context: {json.dumps(context, default=str)}",
                }
            )

        memory_snippets = await self._memory_snippets(goal_text)
        if memory_snippets:
            messages.append(
                {
                    "role": "system",
                    "content": "Relevant memory items (most similar first):\n"
                    + "\n".join(f"- {snippet}" for snippet in memory_snippets),
                }
            )

        messages.append({"role": "user", "content": goal_text})
        return messages

    async def _memory_snippets(self, goal_text: str) -> list[str]:
        if self.memory is None or not hasattr(self.memory, "retrieve_memory"):
            return []
        try:
            results = await self.memory.retrieve_memory(
                goal_text, top_k=self.memory_top_k
            )
        except Exception:
            return []

        snippets: list[str] = []
        for item in results[: self.memory_top_k]:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                snippet = str(text).strip()
            else:
                snippet = str(item).strip()
            if snippet:
                snippets.append(snippet)
        return snippets

    async def decompose(
        self,
        goal_text: str,
        context: dict[str, Any] | None = None,
    ) -> GoalTree:
        if self.llm_manager is None or not hasattr(self.llm_manager, "generate"):
            return self._fallback_tree(goal_text, context or {})

        validation_error: str | None = None
        last_error: Exception | None = None
        for _ in range(3):
            messages = await self._build_messages(goal_text, context)
            if validation_error:
                messages.insert(
                    1,
                    {
                        "role": "system",
                        "content": f"Validation error from previous attempt: {validation_error}",
                    },
                )
            try:
                result = await self.llm_manager.generate(
                    messages=messages, temperature=0.2
                )
                payload = json.loads(result.get("text", "{}"))
                plan = PlannedGoalPlan.parse_obj(payload)
                self._validate_plan(plan)
                return self._plan_to_tree(plan, context or {})
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                validation_error = str(exc)
                last_error = exc

        if last_error is not None:
            raise ValueError(f"Could not build goal plan: {last_error}")
        return self._fallback_tree(goal_text, context or {})

    def _validate_plan(self, plan: PlannedGoalPlan) -> None:
        leaf_count = 0

        def walk(node: PlannedGoalNode, depth: int) -> None:
            nonlocal leaf_count
            if depth > self.max_nesting:
                raise ValueError("Goal plan exceeds maximum nesting depth")
            if node.children:
                for child in node.children:
                    walk(child, depth + 1)
                return
            leaf_count += 1
            if leaf_count > self.max_leaf_nodes:
                raise ValueError("Goal plan exceeds maximum leaf nodes")
            if (
                node.tool
                and self.available_tools
                and node.tool not in self.available_tools
            ):
                raise ValueError(f"Unknown tool: {node.tool}")
            if self._is_destructive(node.text, node.tool):
                node.destructive = True

        for step in plan.steps:
            walk(step, 1)

    def _plan_to_tree(self, plan: PlannedGoalPlan, context: dict[str, Any]) -> GoalTree:
        root = GoalNode(text=plan.root_goal, level=0)
        for step in plan.steps:
            root.add_child(self._node_from_plan(step, level=1))
        return GoalTree(
            root=root,
            root_goal=plan.root_goal,
            clarification_needed=plan.clarification_needed,
            clarification_question=plan.clarification_question,
            context=context,
        )

    def _node_from_plan(self, node: PlannedGoalNode, level: int) -> GoalNode:
        goal_node = GoalNode(
            text=node.text,
            level=level,
            tool=node.tool,
            tool_params=node.params or None,
            requires=list(node.requires),
            destructive=bool(node.destructive)
            or self._is_destructive(node.text, node.tool),
            status=GoalStatus.PENDING,
        )
        for child in node.children:
            goal_node.add_child(self._node_from_plan(child, level=level + 1))
        return goal_node

    def _fallback_tree(self, goal_text: str, context: dict[str, Any]) -> GoalTree:
        root = GoalNode(text=goal_text, level=0)
        root.add_child(GoalNode(text=goal_text, level=1))
        return GoalTree(root=root, root_goal=goal_text, context=context)

    @staticmethod
    def _is_destructive(text: str, tool: Optional[str]) -> bool:
        haystack = f"{text} {tool or ''}".lower()
        return any(
            token in haystack
            for token in [
                "delete",
                "remove",
                "destroy",
                "kill",
                "rm -rf",
                "payment",
                "send message",
                "network send",
            ]
        )
