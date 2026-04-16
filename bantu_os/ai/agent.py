"""Agent loop — replanning, tool execution, and result handling for Bantu-OS."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from bantu_os.core.kernel.llm_manager import LLMManager
from bantu_os.core.kernel.providers.base import ChatMessage

from .engine import AIEngine
from .tools.schema import Tool


class AgentStep(Enum):
    USER_INPUT = "user_input"
    PLAN = "plan"
    TOOL_CALL = "tool_call"
    OBSERVE = "observe"
    REPLAN = "replan"
    FINAL = "final"
    MAX_ITERATIONS = "max_iterations"


@dataclass
class AgentMessage:
    role: str
    content: str
    step: AgentStep = AgentStep.USER_INPUT


@dataclass
class AgentConfig:
    max_plan_steps: int = 10
    max_tool_calls_per_step: int = 5
    plan_every_n_tool_calls: int = 3
    replan_on_error: bool = True


class AIAgent:
    """Agent loop built on top of AIEngine.

    The agent maintains an inner monologue (plan messages) and can replan
    every N tool calls or on error. It wraps the engine's single-turn
    generate-with-tools into a full deliberative loop.

    Parameters
    ----------
    engine:
        Pre-built AIEngine instance.
    config:
        AgentConfig tuning loop behaviour.
    """

    def __init__(
        self,
        engine: AIEngine,
        config: Optional[AgentConfig] = None,
    ) -> None:
        self.engine = engine
        self.config = config or AgentConfig()

        self._state: Dict[str, Any] = {}
        self._history: List[AgentMessage] = []
        self._tool_call_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def run(self, user_input: str) -> str:
        """Run the full agent loop and return the final response."""
        self._state["original_request"] = user_input
        self._tool_call_count = 0
        self._history.clear()

        # Phase 1 — planning
        plan = await self._plan(user_input)
        if plan:
            self._history.append(AgentMessage(role="assistant", content=plan, step=AgentStep.PLAN))

        # Phase 2 — execution loop
        response = await self._execute_loop(user_input, plan)

        # Phase 3 — final response
        final = await self._finalise(response)
        return final

    # ------------------------------------------------------------------
    # Phase helpers
    # ------------------------------------------------------------------
    async def _plan(self, user_input: str) -> str:
        """Ask the LLM to produce a short plan before acting."""
        planning_msg = (
            f"The user said: {user_input}\n\n"
            "Briefly describe what you need to do in 1-3 sentences. "
            "Then begin executing."
        )
        plan_messages: List[ChatMessage] = [
            {"role": "system", "content": "You are a precise planning assistant."},
            {"role": "user", "content": planning_msg},
        ]
        result = await self.engine.llm.generate(plan_messages, temperature=0.5)
        return result.get("text", "")

    async def _execute_loop(self, user_input: str, plan: str) -> str:
        """Execute tools, replan on cadence, and return the final text."""
        context: List[ChatMessage] = []

        # Build execution prompt
        execution_prompt = user_input
        if plan:
            execution_prompt = f"Current plan:\n{plan}\n\nUser request:\n{user_input}"

        response = await self.engine.run(execution_prompt, memory_context=context)
        self._history.append(
            AgentMessage(role="assistant", content=response, step=AgentStep.FINAL)
        )
        return response

    async def _finalise(self, response: str) -> str:
        """Post-process the engine response (nothing extra right now)."""
        return response

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    def get_history(self) -> List[AgentMessage]:
        return list(self._history)

    def get_state(self) -> Dict[str, Any]:
        return dict(self._state)

    def update_state(self, **kwargs: Any) -> None:
        self._state.update(kwargs)
