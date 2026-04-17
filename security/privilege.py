"""
Bantu-OS Privilege Model

Defines what actions require user confirmation vs. auto-approved.
Each action is classified by risk level.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional


class PrivilegeLevel(Enum):
    """Classification of privilege for an action."""
    AUTO = auto()      # No confirmation needed
    CONFIRM = auto()  # User must explicitly approve
    DENY = auto()     # Never allowed


@dataclass
class Action:
    """Represents a potentially privileged action."""
    name: str
    description: str
    level: PrivilegeLevel
    patterns: list[re.Pattern] = field(default_factory=list)
    callback: Optional[Callable[[], bool]] = None


class PrivilegeModel:
    """
    Manages privilege classification for AI actions.

    Actions are checked in order; first match determines the privilege level.
    """

    def __init__(self):
        self._actions: list[Action] = []
        self._setup_default_actions()

    def _setup_default_actions(self) -> None:
        """Register the default action classifications."""

        # === AUTO-APPROVE (low risk) ===
        self.register(Action(
            name="read_public",
            description="Read public documentation and knowledge",
            level=PrivilegeLevel.AUTO,
            patterns=[
                re.compile(r"^read\s+public\s+", re.IGNORECASE),
                re.compile(r"^what(is|are)\s+\w+\s*\??$", re.IGNORECASE),
                re.compile(r"^explain\s+", re.IGNORECASE),
                re.compile(r"^help\s+", re.IGNORECASE),
            ],
        ))

        self.register(Action(
            name="calculate",
            description="Perform calculations and data transformations",
            level=PrivilegeLevel.AUTO,
            patterns=[
                re.compile(r"^calc(ulate)?\s+", re.IGNORECASE),
                re.compile(r"^convert\s+", re.IGNORECASE),
                re.compile(r"^compute\s+", re.IGNORECASE),
            ],
        ))

        self.register(Action(
            name="display_user_file",
            description="Display the user's own files",
            level=PrivilegeLevel.AUTO,
            patterns=[
                re.compile(r"^cat\s+[~/][^\s]+$"),
                re.compile(r"^show\s+(me\s+)?(my\s+)?", re.IGNORECASE),
                re.compile(r"^display\s+", re.IGNORECASE),
            ],
        ))

        # === CONFIRM REQUIRED (medium-high risk) ===
        self.register(Action(
            name="file_write",
            description="Write or modify files outside home directory",
            level=PrivilegeLevel.CONFIRM,
            patterns=[
                re.compile(r"^write\s+", re.IGNORECASE),
                re.compile(r"^create\s+file\s+", re.IGNORECASE),
                re.compile(r"^edit\s+", re.IGNORECASE),
                re.compile(r"^save\s+", re.IGNORECASE),
            ],
        ))

        self.register(Action(
            name="network_request",
            description="Make network requests to third parties",
            level=PrivilegeLevel.CONFIRM,
            patterns=[
                re.compile(r"^fetch\s+", re.IGNORECASE),
                re.compile(r"^curl\s+", re.IGNORECASE),
                re.compile(r"^wget\s+", re.IGNORECASE),
                re.compile(r"^http\s+", re.IGNORECASE),
                re.compile(r"^api\s+", re.IGNORECASE),
            ],
        ))

        self.register(Action(
            name="execute_script",
            description="Run scripts or executables",
            level=PrivilegeLevel.CONFIRM,
            patterns=[
                re.compile(r"^run\s+", re.IGNORECASE),
                re.compile(r"^exec(ute)?\s+", re.IGNORECASE),
                re.compile(r"^bash\s+", re.IGNORECASE),
                re.compile(r"^python\s+", re.IGNORECASE),
            ],
        ))

        self.register(Action(
            name="access_secrets",
            description="Access credential or secrets store",
            level=PrivilegeLevel.CONFIRM,
            patterns=[
                re.compile(r"^get\s+secret", re.IGNORECASE),
                re.compile(r"^read\s+(api\s+)?key", re.IGNORECASE),
                re.compile(r"^credential", re.IGNORECASE),
            ],
        ))

        self.register(Action(
            name="system_config",
            description="Modify system configuration",
            level=PrivilegeLevel.CONFIRM,
            patterns=[
                re.compile(r"^sudo\s+", re.IGNORECASE),
                re.compile(r"^chmod\s+", re.IGNORECASE),
                re.compile(r"^chown\s+", re.IGNORECASE),
                re.compile(r"^systemctl\s+", re.IGNORECASE),
                re.compile(r"^set\s+env(ironment)?\s+", re.IGNORECASE),
            ],
        ))

        # === DENY (high risk / never allowed) ===
        self.register(Action(
            name="disable_security",
            description="Disable or bypass security controls",
            level=PrivilegeLevel.DENY,
            patterns=[
                re.compile(r"^disable\s+(security|firewall|selinux|apparmor)", re.IGNORECASE),
                re.compile(r"^turn\s+off\s+(security|firewall)", re.IGNORECASE),
                re.compile(r"^unset\s+ENFORCE", re.IGNORECASE),
            ],
        ))

        self.register(Action(
            name="privilege_escalation",
            description="Attempt to gain elevated privileges",
            level=PrivilegeLevel.DENY,
            patterns=[
                re.compile(r"^sudo\s+su\b"),
                re.compile(r"^su\s+-?\s*root"),
                re.compile(r"^chmod\s+777\s+"),
                re.compile(r"^passwd\s+root"),
            ],
        ))

        self.register(Action(
            name="boot_tampering",
            description="Modify boot chain or init",
            level=PrivilegeLevel.DENY,
            patterns=[
                re.compile(r"^modify\s+grub", re.IGNORECASE),
                re.compile(r"^edit\s+/boot/", re.IGNORECASE),
                re.compile(r"^inject\s+(into\s+)?init", re.IGNORECASE),
                re.compile(r"^replace\s+(kernel|systemd)", re.IGNORECASE),
            ],
        ))

        self.register(Action(
            name="secret_exfiltration",
            description="Extract or exfiltrate secrets",
            level=PrivilegeLevel.DENY,
            patterns=[
                re.compile(r"^print\s+env\s*$", re.IGNORECASE),
                re.compile(r"^echo\s+\$", re.IGNORECASE),
                re.compile(r"^export\s+$", re.IGNORECASE),
                re.compile(r"^read\s+/proc/\d+/environ", re.IGNORECASE),
            ],
        ))

    def register(self, action: Action) -> None:
        """Register an action classification."""
        self._actions.append(action)

    def classify(self, user_input: str) -> tuple[Action, PrivilegeLevel]:
        """
        Classify user input against registered actions.

        Returns:
            Tuple of (matched Action, PrivilegeLevel).
        """
        for action in self._actions:
            for pattern in action.patterns:
                if pattern.search(user_input):
                    return action, action.level
        # Default: require confirmation for unknown actions
        return Action(
            name="unknown",
            description="Unknown action",
            level=PrivilegeLevel.CONFIRM,
        ), PrivilegeLevel.CONFIRM

    def requires_confirmation(self, user_input: str) -> bool:
        """Check if input requires user confirmation."""
        _, level = self.classify(user_input)
        return level == PrivilegeLevel.CONFIRM

    def is_allowed(self, user_input: str) -> bool:
        """Check if input is allowed (not denied)."""
        _, level = self.classify(user_input)
        return level != PrivilegeLevel.DENY

    def get_confirmation_prompt(self, user_input: str) -> str:
        """Get a human-readable confirmation prompt."""
        action, _ = self.classify(user_input)
        return (
            f"⚠️ This action ({action.name}) requires confirmation:\n"
            f"{action.description}\n\n"
            f"Proceed?"
        )


# Global instance
_default_model: Optional[PrivilegeModel] = None


def get_model() -> PrivilegeModel:
    """Get the default privilege model instance."""
    global _default_model
    if _default_model is None:
        _default_model = PrivilegeModel()
    return _default_model


def requires_confirmation(user_input: str) -> bool:
    """Convenience function to check if input requires confirmation."""
    return get_model().requires_confirmation(user_input)


def is_allowed(user_input: str) -> bool:
    """Convenience function to check if input is allowed."""
    return get_model().is_allowed(user_input)
