"""
Interactive shell for Bantu OS.
"""

import cmd
from typing import Any, Dict


class Shell(cmd.Cmd):
    """Interactive shell for Bantu OS."""

    prompt = "bantu> "
    intro = "Welcome to Bantu OS. Type help or ? to list commands.\n"

    def __init__(self, commands: Dict[str, Any] = None):
        super().__init__()
        self.commands = commands or {}
        self._register_commands()

    def _register_commands(self):
        """Register all available commands."""
        for name, func in self.commands.items():
            setattr(self, f"do_{name}", func)

    def emptyline(self) -> bool:
        """Do nothing on empty input."""
        return False

    def default(self, line: str) -> bool:
        """Handle unknown commands with a helpful error message."""
        cmd_name = line.split()[0] if line.split() else ""
        print(f"Unknown command: '{cmd_name}'. Type 'help' for available commands.")
        return False

    def do_help(self, arg: str) -> None:
        """List available commands with their descriptions.

        Usage: help [command]
          Without arguments: lists all available commands
          With command name: shows detailed help for that command
        """
        if arg.strip():
            self._show_command_help(arg.strip())
        else:
            self._list_all_commands()

    def _list_all_commands(self) -> None:
        """List all available commands with brief descriptions."""
        print("\nAvailable commands:")
        print("-" * 40)

        # Built-in commands
        builtins = {
            "help": "Show this help message",
            "exit": "Exit the shell",
            "quit": "Exit the shell",
        }

        for name, desc in builtins.items():
            print(f"  {name:<12} - {desc}")

        # Registered commands from the command registry
        if self.commands:
            print("\nApplication commands:")
            print("-" * 40)
            for name, func in sorted(self.commands.items()):
                doc = getattr(func, "__doc__", None) or "No description"
                # Use first line of docstring as brief description
                brief = doc.strip().split("\n")[0].strip()
                print(f"  {name:<12} - {brief}")

        print("\nType 'help <command>' for detailed info on a specific command.")

    def _show_command_help(self, command_name: str) -> None:
        """Show detailed help for a specific command."""
        # Check built-in commands first
        builtins = ["help", "exit", "quit", "eof"]
        if command_name in builtins:
            func = getattr(self, f"do_{command_name}", None)
            if func:
                doc = getattr(func, "__doc__", None)
                if doc:
                    print(f"\n{command_name}")
                    print("=" * len(command_name))
                    print(doc.strip())
                    return

        # Check registered commands
        if command_name in self.commands:
            func = self.commands[command_name]
            doc = getattr(func, "__doc__", None)
            if doc:
                print(f"\n{command_name}")
                print("=" * len(command_name))
                print(doc.strip())
            else:
                print(f"No help available for '{command_name}'.")
        else:
            print(
                f"Unknown command: '{command_name}'. Type 'help' for available commands."
            )

    def do_exit(self, arg: str) -> bool:
        """Exit the shell."""
        print("Exiting Bantu OS. Goodbye!")
        return True

    def do_quit(self, arg: str) -> bool:
        """Exit the shell."""
        return self.do_exit(arg)

    def do_EOF(self, arg: str) -> bool:
        """Handle EOF (Ctrl+D) to exit."""
        print()
        return self.do_exit(arg)


def run_shell(commands: Dict[str, Any] = None):
    """Run the Bantu OS shell."""
    try:
        Shell(commands).cmdloop()
    except KeyboardInterrupt:
        print("\nUse 'exit' or 'quit' to exit the shell.")
    except Exception as e:
        print(f"Error: {e}")
