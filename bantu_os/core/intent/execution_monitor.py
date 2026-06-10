from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class GoalEvent:
    type: str
    node_id: str
    message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionMonitor:
    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds
        self.events: list[GoalEvent] = []

    def emit(self, event_type: str, node_id: str, message: str = "") -> GoalEvent:
        event = GoalEvent(type=event_type, node_id=node_id, message=message)
        self.events.append(event)
        return event

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "type": event.type,
                "node_id": event.node_id,
                "message": event.message,
                "created_at": event.created_at.isoformat(),
            }
            for event in self.events
        ]
