""
Command Line Interface for Bantu OS.
"""

from .shell import Shell
from .commands import register_commands

__all__ = ['Shell', 'register_commands']
