"""
Bantu-OS Agent Manager
Layer 4: Multi-agent orchestration with tool execution and message passing.
"""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional



class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"


@dataclass
class AgentMessage:
    id: str
    from_agent: str
    to_agent: str
    type: str
    payload: dict
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolCall:
    id: str
    tool: str
    args: dict
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None


@dataclass
class AgentResult:
    success: bool
    output: str
    tool_calls: list[ToolCall]
    error: Optional[str] = None


class BaseAgent(ABC):
    def __init__(self, name: str, model: str = "gpt-4o"):
        self.name = name
        self.model = model
        self.state = AgentState.IDLE
        self.context: dict = {}
        self._tool_registry: dict[str, Callable] = {}
        self._tool_calls: list[ToolCall] = []

    def register_tool(self, name: str, fn: Callable) -> None:
        self._tool_registry[name] = fn

    async def call_tool(self, tool: str, args: dict) -> Any:
        if tool not in self._tool_registry:
            raise ValueError(f"Unknown tool: {tool}")
        tc = ToolCall(
            id=f"tc_{len(self._tool_calls)+1}",
            tool=tool,
            args=args,
            started_at=time.time(),
        )
        self._tool_calls.append(tc)
        try:
            result = self._tool_registry[tool](**args)
            if asyncio.iscoroutine(result):
                result = await result
            tc.result = result
            tc.finished_at = time.time()
            return result
        except Exception as e:
            tc.error = str(e)
            tc.finished_at = time.time()
            raise

    @abstractmethod
    async def think(self, prompt: str) -> str:
        raise NotImplementedError

    async def run(self, prompt: str) -> AgentResult:
        self.state = AgentState.THINKING
        self._tool_calls.clear()
        try:
            output = await self.think(prompt)
            self.state = AgentState.DONE
            return AgentResult(success=True, output=output, tool_calls=self._tool_calls)
        except Exception as e:
            self.state = AgentState.ERROR
            return AgentResult(
                success=False, output="", tool_calls=self._tool_calls, error=str(e)
            )


class ShellAgent(BaseAgent):
    """Executes shell commands safely."""

    def __init__(self):
        super().__init__("shell")

    async def think(self, prompt: str) -> str:
        import subprocess

        result = subprocess.run(
            prompt, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout or result.stderr


class TaskAgent(BaseAgent):
    """Breaks down tasks into subtasks and manages lifecycle."""

    def __init__(self):
        super().__init__("task")
        self.tasks: dict[str, dict] = {}

    def create_task(self, task_id: str, description: str, params: dict) -> None:
        self.tasks[task_id] = {
            "description": description,
            "params": params,
            "status": "pending",
        }

    async def think(self, prompt: str) -> str:
        lines = [l.strip() for l in prompt.split("\n") if l.strip()]
        return json.dumps({"tasks_created": len(lines), "tasks": lines})


class MemoryAgent(BaseAgent):
    """Semantic memory retrieval and storage."""

    def __init__(self):
        super().__init__("memory")
        self._store: dict[str, Any] = {}

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        q = query.lower()
        scored = [
            (k, sum(w in v.lower() for w in q.split())) for k, v in self._store.items()
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [{"id": k, "text": self._store[k]} for k, _ in scored[:top_k] if _ > 0]

    def store(self, id: str, text: str) -> None:
        self._store[id] = text

    async def think(self, prompt: str) -> str:
        if prompt.lower().startswith("store:"):
            _, id, text = prompt.split(":", 2)
            self.store(id.strip(), text.strip())
            return f"Stored: {id}"
        elif prompt.lower().startswith("retrieve:"):
            query = prompt.split(":", 1)[1].strip()
            results = self.retrieve(query)
            return json.dumps(results)
        return json.dumps({"error": "Unknown intent"})


class AgentManager:
    """Central agent orchestrator — routes prompts through kernel and executes tools."""

    def __init__(self, kernel=None, tools: dict[str, Callable] | None = None):
        self.kernel = kernel
        self._tools: dict[str, Callable] = tools.copy() if tools else {}
        self._sub_agents: dict[str, BaseAgent] = {}
        self._mailbox: dict[str, list[AgentMessage]] = {}

    # -------------------------------------------------------------------------
    # Tool registry
    # -------------------------------------------------------------------------
    def register_tool(self, name: str, fn: Callable) -> None:
        """Register a callable tool by name."""
        self._tools[name] = fn

    @property
    def tools(self) -> dict[str, Callable]:
        """Expose tools dict for backward-compatibility with tests."""
        return self._tools

    # -------------------------------------------------------------------------
    # Tool execution helpers
    # -------------------------------------------------------------------------
    async def _execute_tool_call(self, tool_name: str, args: dict) -> str:
        """Run a single registered tool and return its result as a string."""
        if tool_name not in self._tools:
            return f"Unknown tool: {tool_name}"
        try:
            result = self._tools[tool_name](**args)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)
        except TypeError as e:
            return f"Tool '{tool_name}' argument error: {e}"
        except Exception as e:
            return f"Tool '{tool_name}' failed: {e}"

    async def _parse_and_dispatch(self, text: str) -> str:
        """Ask the kernel to decide what to do, then execute the tool."""
        if self.kernel is None:
            return "AgentManager has no kernel — cannot process input"

        raw = await self.kernel.process_input(text)

        # Try JSON action dispatch
        try:
            parsed = json.loads(raw)
            action = parsed.get("action", "")
            args = parsed.get("args", {})
        except (json.JSONDecodeError, TypeError):
            # Not JSON — treat raw text as direct response
            return raw

        if action == "respond":
            return args.get("message", raw)
        if action in self._tools:
            return await self._execute_tool_call(action, args)
        return f"Unknown tool: {action}"

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    async def execute(self, prompt: str) -> str:
        """
        Process a prompt: kernel decides, tool gets executed.
        Returns the tool result or kernel response as a string.
        """
        return await self._parse_and_dispatch(prompt)

    def register(self, agent: BaseAgent) -> None:
        """Register a sub-agent for dispatch-based routing."""
        self._sub_agents[agent.name] = agent

    async def dispatch(self, agent_name: str, prompt: str) -> AgentResult:
        """Dispatch to a named sub-agent."""
        if agent_name not in self._sub_agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        return await self._sub_agents[agent_name].run(prompt)

    def send_message(
        self, from_agent: str, to_agent: str, msg_type: str, payload: dict
    ) -> None:
        msg = AgentMessage(
            id=f"msg_{int(time.time()*1000)}",
            from_agent=from_agent,
            to_agent=to_agent,
            type=msg_type,
            payload=payload,
        )
        self._mailbox.setdefault(to_agent, []).append(msg)

    def get_messages(self, agent_name: str) -> list[AgentMessage]:
        msgs = self._mailbox.get(agent_name, [])
        self._mailbox[agent_name] = []
        return msgs

    def list_agents(self) -> list[str]:
        return list(self._sub_agents.keys())

    # -------------------------------------------------------------------------
    # Mailbox (used by send_message / get_messages)
    # -------------------------------------------------------------------------
    _mailbox: dict[str, list[AgentMessage]] = {}
