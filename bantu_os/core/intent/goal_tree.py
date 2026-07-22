from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


class GoalStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass(slots=True)
class RetryRecord:
    reason: str
    attempted_plan: str = ""
    error: str = ""
    attempted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "attempted_plan": self.attempted_plan,
            "error": self.error,
            "attempted_at": self.attempted_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RetryRecord":
        attempted_at = data.get("attempted_at")
        if isinstance(attempted_at, str):
            attempted_at_dt = datetime.fromisoformat(attempted_at)
        else:
            attempted_at_dt = datetime.now(timezone.utc)
        return cls(
            reason=str(data.get("reason", "")),
            attempted_plan=str(data.get("attempted_plan", "")),
            error=str(data.get("error", "")),
            attempted_at=attempted_at_dt,
        )


@dataclass(slots=True)
class GoalNode:
    text: str
    level: int = 0
    status: GoalStatus = GoalStatus.PENDING
    tool: Optional[str] = None
    tool_params: Optional[dict[str, Any]] = None
    result: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    retry_history: list[RetryRecord] = field(default_factory=list)
    children: list["GoalNode"] = field(default_factory=list)
    parent_id: Optional[str] = None
    requires: list[str] = field(default_factory=list)
    destructive: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    id: str = field(default_factory=lambda: uuid4().hex)

    def add_child(self, child: "GoalNode") -> "GoalNode":
        child.parent_id = self.id
        child.level = self.level + 1
        self.children.append(child)
        return child

    def is_leaf(self) -> bool:
        return not self.children

    def mark_done(self, result: Optional[str] = None) -> None:
        self.status = GoalStatus.DONE
        self.result = result
        self.completed_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        self.status = GoalStatus.FAILED
        self.error = error
        self.completed_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "level": self.level,
            "status": self.status.value,
            "tool": self.tool,
            "tool_params": self.tool_params,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "retry_history": [item.to_dict() for item in self.retry_history],
            "children": [child.to_dict() for child in self.children],
            "parent_id": self.parent_id,
            "requires": list(self.requires),
            "destructive": self.destructive,
            "created_at": self.created_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoalNode":
        created_at = data.get("created_at")
        completed_at = data.get("completed_at")
        node = cls(
            id=str(data.get("id") or uuid4().hex),
            text=str(data.get("text", "")),
            level=int(data.get("level", 0)),
            status=GoalStatus(str(data.get("status", GoalStatus.PENDING.value))),
            tool=data.get("tool"),
            tool_params=data.get("tool_params") or None,
            result=data.get("result"),
            error=data.get("error"),
            retry_count=int(data.get("retry_count", 0)),
            retry_history=[
                RetryRecord.from_dict(item) for item in data.get("retry_history", [])
            ],
            parent_id=data.get("parent_id"),
            requires=list(data.get("requires", [])),
            destructive=bool(data.get("destructive", False)),
            created_at=(
                datetime.fromisoformat(created_at)
                if isinstance(created_at, str)
                else datetime.now(timezone.utc)
            ),
            completed_at=(
                datetime.fromisoformat(completed_at)
                if isinstance(completed_at, str) and completed_at
                else None
            ),
        )
        node.children = [cls.from_dict(item) for item in data.get("children", [])]
        for child in node.children:
            child.parent_id = node.id
        return node


@dataclass(slots=True)
class GoalTree:
    root: GoalNode
    root_goal: str = ""
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.root_goal:
            self.root_goal = self.root.text

    def iter_nodes(self) -> list[GoalNode]:
        nodes: list[GoalNode] = []

        def walk(node: GoalNode) -> None:
            nodes.append(node)
            for child in node.children:
                walk(child)

        walk(self.root)
        return nodes

    def leaf_nodes(self) -> list[GoalNode]:
        return [node for node in self.iter_nodes() if node.is_leaf()]

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_goal": self.root_goal,
            "clarification_needed": self.clarification_needed,
            "clarification_question": self.clarification_question,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "root": self.root.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoalTree":
        created_at = data.get("created_at")
        return cls(
            root=GoalNode.from_dict(data["root"]),
            root_goal=str(data.get("root_goal", "")),
            clarification_needed=bool(data.get("clarification_needed", False)),
            clarification_question=data.get("clarification_question"),
            context=dict(data.get("context", {})),
            created_at=(
                datetime.fromisoformat(created_at)
                if isinstance(created_at, str)
                else datetime.now(timezone.utc)
            ),
        )
