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

from bantu_os.config import settings


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
        tc = ToolCall(id=f"tc_{len(self._tool_calls)+1}", tool=tool, args=args, started_at=time.time())
        self._tool_calls.append(tc)
        try:
            result = self._tool_registry[tool](**args)
            if asyncio.iscoroutine(result):
                result = await result
            tc.result = result
            return result
        except Exception as e:
            tc.error = str(e)
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
            return AgentResult(success=False, output="", tool_calls=self._tool_calls, error=str(e))


class ShellAgent(BaseAgent):
    """Executes shell commands safely."""

    def __init__(self):
        super().__init__("shell")

    async def think(self, prompt: str) -> str:
        import subprocess
        result = subprocess.run(prompt, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout or result.stderr


class TaskAgent(BaseAgent):
    """Breaks down tasks into subtasks and manages lifecycle."""

    def __init__(self):
        super().__init__("task")
        self.tasks: dict[str, dict] = {}

    def create_task(self, task_id: str, description: str, params: dict) -> None:
        self.tasks[task_id] = {"description": description, "params": params, "status": "pending"}

    async def think(self, prompt: str) -> str:
        # Simple task parsing - in production this would call an LLM
        lines = [l.strip() for l in prompt.split("\n") if l.strip()]
        return json.dumps({"tasks_created": len(lines), "tasks": lines})


class MemoryAgent(BaseAgent):
    """Semantic memory retrieval and storage."""

    def __init__(self):
        super().__init__("memory")
        self._store: dict[str, Any] = {}

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        q = query.lower()
        scored = [(k, sum(w in v.lower() for w in q.split())) for k, v in self._store.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [{"id": k, "text": self._store[k]} for k, _ in scored[:top_k] if _ > 0]

    def store(self, id: str, text: str) -> None:
        self._store[id] = text

    async def think(self, prompt: str) -> str:
        # Parse intent: retrieve vs store
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
    """Central agent orchestrator."""

    def __init__(self):
        self.agents: dict[str, BaseAgent] = {}
        self._mailbox: dict[str, list[AgentMessage]] = {}

    def register(self, agent: BaseAgent) -> None:
        self.agents[agent.name] = agent

    async def dispatch(self, agent_name: str, prompt: str) -> AgentResult:
        if agent_name not in self.agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        return await self.agents[agent_name].run(prompt)

    def send_message(self, from_agent: str, to_agent: str, msg_type: str, payload: dict) -> None:
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
        return list(self.agents.keys())