"""
CLI Commands for Bantu OS.
"""
from typing import Dict, Callable, Any

def register_commands(shell: Any) -> Dict[str, Callable]:
    """Register all available commands."""
    commands = {
        'help': shell.do_help,
        'exit': shell.do_exit,
        'quit': shell.do_quit,
        'version': show_version,
        'status': show_status,
    }
    return commands

def show_version(_: str) -> None:
    """Show Bantu OS version."""
    from bantu_os.core import __version__
    print(f"Bantu OS v{__version__}")

def show_status(_: str) -> None:
    """Show system status."""
    print("Bantu OS Status:")
    print("- System: Operational")
    print("- Memory: Available")
    print("- Agents: Ready")
