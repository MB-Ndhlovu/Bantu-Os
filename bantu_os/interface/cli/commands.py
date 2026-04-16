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
        'clear': clear_screen,
    }
    return commands


def show_version(_: str) -> None:
    """Show Bantu OS version.
    
    Displays the current installed version of Bantu OS.
    Example: version
    """
    from bantu_os.core import __version__
    print(f"Bantu OS v{__version__}")


def show_status(_: str) -> None:
    """Show system status.
    
    Displays the current operational status of Bantu OS subsystems.
    Shows status for: System, Memory, and Agents.
    Example: status
    """
    print("Bantu OS Status:")
    print("- System: Operational")
    print("- Memory: Available")
    print("- Agents: Ready")


def clear_screen(_: str) -> None:
    """Clear the terminal screen.
    
    Clears all visible content from the terminal display.
    Useful for decluttering the workspace during long sessions.
    Example: clear
    """
    import os
    os.system('cls' if os.name == 'nt' else 'clear')