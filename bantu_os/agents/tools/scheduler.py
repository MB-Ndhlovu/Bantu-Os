"""
Scheduler tool wrappers that expose add_event, list_events, remove_event.

They adapt a SchedulingAgent instance to simple callables usable by AgentManager.
If a Memory instance is provided, adding an event will also store a memory note.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from ..scheduling_agent import SchedulingAgent
from ...memory.memory import Memory


def make_scheduler_tools(agent: SchedulingAgent, memory: Optional[Memory] = None) -> Dict[str, Callable[..., Any]]:
    """Return tool callables mapped by action names."""

    def add_event(*, title: str, when: str) -> str:
        event_id = agent.add_event(title=title, when_str=when)
        if memory is not None and memory.embeddings is not None:
            try:
                memory_text = f"Event: {title} at {when} (id={event_id})"
                # Fire and forget would be nicer; keep simple and synchronous composition.
                import asyncio
                if asyncio.get_event_loop().is_running():
                    asyncio.create_task(memory.store_text(memory_text))
                else:
                    asyncio.run(memory.store_text(memory_text))
            except Exception:
                pass
        return f"event_id={event_id}"

    def list_events() -> str:
        rows = agent.list_events()
        if not rows:
            return "No events."
        lines = [f"{r.id}\t{r.when_ts}\t{r.title}" for r in rows]
        return "\n".join(lines)

    def remove_event(*, event_id: int) -> str:
        ok = agent.remove_event(event_id)
        return "removed" if ok else "not_found"

    return {
        "add_event": add_event,
        "list_events": list_events,
        "remove_event": remove_event,
    }
