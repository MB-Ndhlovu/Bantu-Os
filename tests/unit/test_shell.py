"""
Tests for the CLI shell and commands.
"""

import sys
from io import StringIO

from bantu_os.interface.cli.commands import clear_screen, show_status, show_version
from bantu_os.interface.cli.shell import Shell


class TestShellHelp:
    """Tests for the help system."""

    def test_help_lists_all_commands(self):
        """Test that help lists all available commands."""
        commands = {
            "version": show_version,
            "status": show_status,
        }
        shell = Shell(commands)

        captured = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured

        shell._list_all_commands()
        output = captured.getvalue()

        sys.stdout = old_stdout

        assert "Available commands" in output
        assert "help" in output
        assert "exit" in output
        assert "quit" in output
        assert "Application commands" in output
        assert "version" in output
        assert "status" in output

    def test_help_shows_command_details(self):
        """Test that help <command> shows detailed info."""
        commands = {
            "version": show_version,
        }
        shell = Shell(commands)

        captured = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured

        shell._show_command_help("version")
        output = captured.getvalue()

        sys.stdout = old_stdout

        assert "Show Bantu OS version" in output

    def test_unknown_command_shows_error(self):
        """Test that unknown commands show helpful error message."""
        shell = Shell({})

        captured = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured

        shell.default("badcommand")
        output = captured.getvalue()

        sys.stdout = old_stdout

        assert "Unknown command" in output
        assert "badcommand" in output


class TestCommands:
    """Tests for individual commands."""

    def test_show_version(self):
        """Test version command output."""
        captured = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured

        show_version("")
        output = captured.getvalue()

        sys.stdout = old_stdout

        assert "Bantu OS" in output

    def test_show_status(self):
        """Test status command output."""
        captured = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured

        show_status("")
        output = captured.getvalue()

        sys.stdout = old_stdout

        assert "Status" in output
        assert "Operational" in output

    def test_clear_screen(self):
        """Test clear command doesn't raise."""
        clear_screen("")


class TestShellEdgeCases:
    """Tests for shell edge cases."""

    def test_emptyline_does_nothing(self):
        """Test that empty line doesn't cause error."""
        shell = Shell({})
        result = shell.emptyline()
        assert result is False

    def test_exit_command_returns_true(self):
        """Test exit command returns True to terminate."""
        shell = Shell({})
        result = shell.do_exit("")
        assert result is True

    def test_quit_command_returns_true(self):
        """Test quit command returns True to terminate."""
        shell = Shell({})
        result = shell.do_quit("")
        assert result is True
