"""
Bantu-OS AI Service Layer
Receives requests via IPC, invokes LLM, returns responses.
Works alongside the Rust shell REPL as the AI brain.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from dataclasses import dataclass, field
from typing import Optional

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("ai_service")


@dataclass
class AIAgent:
    name: str
    system_prompt: str
    tools: list = field(default_factory=list)
    memory_context: list = field(default_factory=list)


class AIService:
    def __init__(self) -> None:
        self.agents: dict[str, AIAgent] = {}
        self.active_agent: Optional[AIAgent] = None
        self._running = False

    def register_agent(
        self, name: str, system_prompt: str, tools: Optional[list] = None
    ) -> None:
        agent = AIAgent(name=name, system_prompt=system_prompt, tools=tools or [])
        self.agents[name] = agent
        logger.info(f"Registered agent: {name}")

    def set_active(self, name: str) -> bool:
        if name in self.agents:
            self.active_agent = self.agents[name]
            return True
        return False

    async def invoke(self, prompt: str, agent_name: Optional[str] = None) -> str:
        agent = (
            self.agents.get(agent_name or "")
            or self.active_agent
            or AIAgent(name="default", system_prompt="You are Bantu OS.")
        )
        logger.info(f"[{agent.name}] IN: {prompt[:80]}...")

        response = f"[Bantu-OS AI] Processed: {prompt[:60]}..."

        logger.info(f"[{agent.name}] OUT: {response[:80]}...")
        return response

    def shutdown(self) -> None:
        self._running = False
        logger.info("AI service shutting down")


async def main() -> None:
    service = AIService()

    # Register core agents
    service.register_agent(
        name="shell_assistant",
        system_prompt="You are the Bantu-OS shell assistant. Help users navigate the OS, execute commands, and manage files.",
        tools=["exec", "read", "write", "list", "search"],
    )
    service.register_agent(
        name="task_agent",
        system_prompt="You manage tasks and scheduling on Bantu-OS.",
        tools=["schedule", "cancel", "list_tasks", "priority"],
    )
    service.register_agent(
        name="memory_agent",
        system_prompt="You manage persistent memory and knowledge on Bantu-OS.",
        tools=["store", "retrieve", "forget", "index"],
    )

    service.set_active("shell_assistant")
    logger.info("Bantu-OS AI service started")

    # Handle signals
    def signal_handler(sig, frame):
        logger.info("Received signal, shutting down...")
        service.shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    service._running = True
    while service._running:
        await asyncio.sleep(1)

    logger.info("AI service stopped")


if __name__ == "__main__":
    asyncio.run(main())
