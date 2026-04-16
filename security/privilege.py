"""
Privilege Model for Bantu-OS

Defines which operations require user confirmation vs. can be
executed autonomously by the AI assistant.

Privilege Levels:
- AUTO: AI can execute without confirmation
- CONFIRM: AI requests permission, user must approve
- DENY: AI cannot execute, requires user to run directly
"""

from __future__ import annotations

import enum
from typing import Any, Callable, Optional


class PrivilegeLevel(enum.IntEnum):
    """Capability-based privilege levels for tool execution."""
    AUTO = 0      # AI executes autonomously
    CONFIRM = 1   # User must confirm before execution
    DENY = 2      # Blocked for AI; user must run directly


class PrivilegeResult:
    """Outcome of a privilege check."""
    def __init__(
        self,
        allowed: bool,
        level: PrivilegeLevel,
        reason: str = "",
        requires_confirmation: bool = False,
    ):
        self.allowed = allowed
        self.level = level
        self.reason = reason
        self.requires_confirmation = requires_confirmation

    def __bool__(self) -> bool:
        return self.allowed


# Default privilege registry
TOOL_PRIVILEGES: dict[str, PrivilegeLevel] = {
    # === AUTO (Level 0): Safe, routine operations ===
    "filesystem.read":         PrivilegeLevel.AUTO,
    "filesystem.list":         PrivilegeLevel.AUTO,
    "calculator.calculate":     PrivilegeLevel.AUTO,
    "web_search.search":       PrivilegeLevel.AUTO,
    "browser.open":            PrivilegeLevel.AUTO,
    "browser.screenshot":      PrivilegeLevel.AUTO,
    "memory.store":            PrivilegeLevel.AUTO,
    "memory.retrieve":         PrivilegeLevel.AUTO,
    "scheduler.list":          PrivilegeLevel.AUTO,
    "scheduler.get":           PrivilegeLevel.AUTO,
    "scheduler.pending":       PrivilegeLevel.AUTO,
    "file_service.read":       PrivilegeLevel.AUTO,
    "file_service.list":       PrivilegeLevel.AUTO,
    "knowledge_graph.query":   PrivilegeLevel.AUTO,
    "knowledge_graph.traverse": PrivilegeLevel.AUTO,

    # === CONFIRM (Level 1): Potentially destructive or far-reaching ===
    "filesystem.write":        PrivilegeLevel.CONFIRM,
    "filesystem.delete":       PrivilegeLevel.CONFIRM,
    "filesystem.move":         PrivilegeLevel.CONFIRM,
    "filesystem.copy":         PrivilegeLevel.CONFIRM,
    "network.request":         PrivilegeLevel.CONFIRM,
    "browser.click":           PrivilegeLevel.CONFIRM,
    "browser.fill":            PrivilegeLevel.CONFIRM,
    "browser.submit":          PrivilegeLevel.CONFIRM,
    "scheduler.create":        PrivilegeLevel.CONFIRM,
    "scheduler.cancel":        PrivilegeLevel.CONFIRM,
    "scheduler.update":       PrivilegeLevel.CONFIRM,
    "memory.forget":           PrivilegeLevel.CONFIRM,
    "knowledge_graph.add_node":  PrivilegeLevel.CONFIRM,
    "knowledge_graph.add_edge":  PrivilegeLevel.CONFIRM,
    "file_service.write":      PrivilegeLevel.CONFIRM,
    "file_service.delete":     PrivilegeLevel.CONFIRM,

    # === DENY (Level 2): Never execute autonomously ===
    "process.spawn":           PrivilegeLevel.DENY,
    "process.kill":            PrivilegeLevel.DENY,
    "service.restart":         PrivilegeLevel.DENY,
    "service.stop":            PrivilegeLevel.DENY,
    "service.start":           PrivilegeLevel.DENY,
    "package.install":         PrivilegeLevel.DENY,
    "package.remove":          PrivilegeLevel.DENY,
    "user.create":            PrivilegeLevel.DENY,
    "user.delete":            PrivilegeLevel.DENY,
    "secrets.set":             PrivilegeLevel.DENY,
    "secrets.delete":         PrivilegeLevel.DENY,
    "shell.exec":             PrivilegeLevel.DENY,
}


def get_privilege(tool_name: str) -> PrivilegeLevel:
    """Get the privilege level for a tool."""
    return TOOL_PRIVILEGES.get(tool_name, PrivilegeLevel.CONFIRM)


def check_privilege(
    tool_name: str,
    args: Optional[dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> PrivilegeResult:
    """
    Check if an AI can execute a tool at a given privilege level.

    Returns a PrivilegeResult with the decision and metadata.
    """
    level = get_privilege(tool_name)

    if level == PrivilegeLevel.AUTO:
        return PrivilegeResult(
            allowed=True,
            level=level,
            reason="Tool is in auto-execute allowlist",
            requires_confirmation=False,
        )

    if level == PrivilegeLevel.DENY:
        return PrivilegeResult(
            allowed=False,
            level=level,
            reason="Tool is blocked for autonomous AI execution",
            requires_confirmation=False,
        )

    # CONFIRM level
    return PrivilegeResult(
        allowed=True,
        level=level,
        reason="Tool requires user confirmation before execution",
        requires_confirmation=True,
    )


def set_privilege(tool_name: str, level: PrivilegeLevel) -> None:
    """Override the privilege level for a specific tool."""
    TOOL_PRIVILEGES[tool_name] = level


def require_confirmation(tool_name: str) -> bool:
    """Shorthand: returns True if the tool requires user confirmation."""
    return get_privilege(tool_name) == PrivilegeLevel.CONFIRM


def is_allowed(tool_name: str) -> bool:
    """Shorthand: returns True if the tool can be executed by AI (with or without confirm)."""
    level = get_privilege(tool_name)
    return level != PrivilegeLevel.DENY
