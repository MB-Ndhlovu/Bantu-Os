"""
AgentManager - Orchestrates tool usage on top of the Kernel.

Flow:
- User input -> Kernel interprets into a structured action (JSON)
- AgentManager selects and executes the right tool
- Returns the tool result or a direct response

The interpretation prompt is provider-agnostic JSON. Example expected output:
{
  "thought": "I should use the calculator",
  "action": "calculator",
  "args": {"expression": "2 + 2 * 3"}
}
If no tool is needed, the Kernel should return:
{
  "action": "respond",
  "args": {"message": "..."}
}
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, Optional

from .task_manager import TaskManager
from ..core.kernel.kernel import Kernel


INTERPRETER_SYSTEM_PROMPT = (
    "You are a tool-using agent. Given a user's input, decide whether to use a tool "
    "and respond in strict JSON ONLY with keys: thought (string), action (string), args (object). "
    "Use 'respond' as action when a direct answer is sufficient."
)


class AgentManager:
    """Agent manager that mediates between the Kernel and registered tools."""

    def __init__(
        self,
        kernel: Optional[Kernel] = None,
        tools: Optional[Dict[str, Callable[..., Any]]] = None,
    ) -> None:
        self.kernel = kernel or Kernel()
        self.tools: Dict[str, Callable[..., Any]] = tools or {}
        self.tasks = TaskManager()

    def register_tool(self, name: str, fn: Callable[..., Any]) -> None:
        """Register a callable tool by name."""
        self.tools[name] = fn

    def unregister_tool(self, name: str) -> None:
        if name in self.tools:
            del self.tools[name]

    async def execute(self, user_input: str) -> str:
        """Interpret user input via Kernel and execute the appropriate tool."""
        # Ask the Kernel to produce an action plan as JSON
        llm_text = await self.kernel.process_input(
            user_input,
            system_prompt=INTERPRETER_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=256,
        )

        action = self._safe_parse_action(llm_text)
        if not action:
            # Fallback: just return the raw model text
            return llm_text

        name = action.get("action")
        args = action.get("args") or {}

        if name == "respond":
            return str(args.get("message", ""))

        if name not in self.tools:
            return f"Unknown tool: {name}"

        try:
            result = self.tools[name](**args)
        except TypeError as e:
            return f"Tool '{name}' argument error: {e}"
        except Exception as e:  # pragma: no cover - unexpected tool errors
            return f"Tool '{name}' failed: {e}"
        return str(result)

    @staticmethod
    def _safe_parse_action(text: str) -> Optional[Dict[str, Any]]:
        """Attempt to parse an action JSON from model text.
        Accepts either a pure JSON string or text containing a JSON block.
        """
        text = text.strip()
        # Try direct JSON
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and "action" in obj:
                return obj
        except Exception:
            pass

        # Try to find the first JSON object in the text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = text[start : end + 1]
            try:
                obj = json.loads(snippet)
                if isinstance(obj, dict) and "action" in obj:
                    return obj
            except Exception:
                pass
        return None
