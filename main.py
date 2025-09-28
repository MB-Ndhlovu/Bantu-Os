"""
Bantu OS CLI entrypoint.

Clean loop: input -> Kernel -> AgentManager (tools) -> Memory -> output

Run with:
  python main.py

Optionally, set OPENAI_API_KEY (or use .env via your workflow) to enable
LLM + embeddings. If no key is present, the app still runs but Kernel/Memory
that require network will fail when invoked.
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional

from bantu_os.core.kernel import Kernel
from bantu_os.agents import AgentManager, calculate, list_dir, read_text, open_url
from bantu_os.agents.tools import web_search
from bantu_os.agents.scheduling_agent import SchedulingAgent
from bantu_os.agents.tools.scheduler import make_scheduler_tools
from bantu_os.memory import Memory, OpenAIEmbeddingsProvider, VectorDBStore


async def build_app() -> tuple[Kernel, AgentManager, Optional[Memory]]:
    """Construct Kernel + Memory + AgentManager and register default tools."""
    # Memory: in-memory store by default
    memory: Optional[Memory] = Memory(store=VectorDBStore(dim=768))

    # If an API key exists, attach OpenAI embeddings to memory for recall
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            memory.set_embeddings_provider(OpenAIEmbeddingsProvider(api_key=api_key))
        except Exception:
            # If embeddings init fails, continue without memory embeddings
            pass

    # Kernel with memory attached (if any)
    kernel = Kernel(
        provider="openai",
        provider_model=None,  # fall back to settings.DEFAULT_LLM_MODEL
        memory=memory,
        memory_top_k=3,
    )

    # AgentManager on top of Kernel
    agent = AgentManager(kernel=kernel)

    # Register built-in tools
    agent.register_tool("calculator", calculate)
    agent.register_tool("list_dir", list_dir)
    agent.register_tool("read_text", read_text)
    agent.register_tool("open_url", open_url)
    agent.register_tool("web_search", web_search)

    # Scheduler tools (SQLite-backed)
    scheduler = SchedulingAgent()
    sched_tools = make_scheduler_tools(scheduler, memory=memory)
    for name, fn in sched_tools.items():
        agent.register_tool(name, fn)

    return kernel, agent, memory


async def repl() -> None:
    """Simple REPL: read a line, execute through AgentManager, print result."""
    _, agent, _ = await build_app()

    print("Welcome to Bantu OS CLI. Type 'exit' or 'quit' to leave.")
    while True:
        try:
            line = input("bantu> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not line:
            continue
        if line.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        try:
            result = await agent.execute(line)
            print(result)
        except Exception as e:
            print(f"Error: {e}")


def main() -> None:
    asyncio.run(repl())


if __name__ == "__main__":
    main()
