"""
Command Line Interface for Bantu OS.
"""

from .commands import register_commands
from .shell import Shell

__all__ = ["Shell", "register_commands"]
