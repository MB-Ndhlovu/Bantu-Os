""
Interactive shell for Bantu OS.
"""
import cmd
import sys
from typing import Dict, Type, Any

class Shell(cmd.Cmd):
    """Interactive shell for Bantu OS."""
    
    prompt = 'bantu> '
    intro = 'Welcome to Bantu OS. Type help or ? to list commands.\n'
    def __init__(self, commands: Dict[str, Any] = None):
        super().__init__()
        self.commands = commands or {}
        self._register_commands()
    
    def _register_commands(self):
        """Register all available commands."""
        for name, func in self.commands.items():
            setattr(self, f'do_{name}', func)
    
    def emptyline(self) -> bool:
        """Do nothing on empty input."""
        return False
    
    def do_exit(self, arg: str) -> bool:
        """Exit the shell."""
        print('Exiting Bantu OS. Goodbye!')
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
        print('\nUse \'exit\' or \'quit\' to exit the shell.')
    except Exception as e:
        print(f'Error: {e}')
