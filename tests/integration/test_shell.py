"""
Smoke test for the Rust shell.

Verifies that bantu_shell (built from shell/) starts, produces expected
banner output, handles "exit" gracefully, and rejects unknown commands.
Requires cargo and a working shell/Cargo.toml in the project root.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SHELL_DIR = REPO_ROOT / "shell"


class TestRustShell:
    """Smoke tests for the Rust shell binary."""

    @pytest.fixture(scope="class")
    def shell_binary(self) -> Path:
        """Build the Rust shell and return the path to the binary."""
        if not SHELL_DIR.exists():
            pytest.skip(f"shell/ directory not found at {SHELL_DIR}")

        cargo = _find_cargo()
        if cargo is None:
            pytest.skip("cargo not found — cannot build Rust shell")

        # Build release binary
        build_result = subprocess.run(
            [
                "cargo",
                "build",
                "--release",
                "--manifest-path",
                str(SHELL_DIR / "Cargo.toml"),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if build_result.returncode != 0:
            pytest.fail(
                f"cargo build failed:\nSTDOUT:\n{build_result.stdout}\nSTDERR:\n{build_result.stderr}"
            )

        binary = SHELL_DIR / "target" / "release" / "bantu_shell"
        if not binary.exists():
            binary = SHELL_DIR / "target" / "release" / "shell"
        if not binary.exists():
            binary = SHELL_DIR / "target" / "debug" / "bantu_shell"
        if not binary.exists():
            pytest.fail(
                f"Expected binary not found after build in {SHELL_DIR / 'target'}"
            )

        return binary

    def test_shell_runs_and_shows_banner(self, shell_binary: Path):
        """Shell should start and print the Bantu-OS banner."""
        proc = subprocess.Popen(
            [str(shell_binary)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(timeout=5)

        assert proc.returncode == 0, f"Shell exited non-zero: {stderr}"
        assert (
            "Bantu-OS Shell" in stdout
        ), f"Expected banner not found in output:\n{stdout}"

    def test_exit_command_terminates_cleanly(self, shell_binary: Path):
        """Sending 'exit' should terminate the shell with exit code 0."""
        proc = subprocess.Popen(
            [str(shell_binary)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(input="exit\n", timeout=5)

        assert (
            proc.returncode == 0
        ), f"Shell should exit cleanly after 'exit' command: {stderr}"
        assert "Goodbye!" in stdout, f"Expected 'Goodbye!' in output:\n{stdout}"

    def test_unknown_command_returns_error_line(self, shell_binary: Path):
        """An unknown command should be echoed back with 'You entered:' prefix."""
        proc = subprocess.Popen(
            [str(shell_binary)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(input="badcommand\n", timeout=5)

        assert proc.returncode == 0, f"Shell exited non-zero: {stderr}"
        # The shell echoes unknown commands as: "You entered: <input>"
        assert (
            "You entered: badcommand" in stdout
        ), f"Expected unknown command echo in output:\n{stdout}"

    def test_empty_line_does_not_crash(self, shell_binary: Path):
        """Sending an empty line (just newline) should not crash the shell."""
        proc = subprocess.Popen(
            [str(shell_binary)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(input="\n", timeout=5)

        # Shell should still be running or exited cleanly
        assert proc.returncode in (
            0,
            1,
        ), f"Shell crashed on empty input. returncode={proc.returncode}\nSTDERR:{stderr}"


def _find_cargo() -> str | None:
    """Return the path to cargo if found, else None."""
    for candidate in ["/usr/bin/cargo", "/usr/local/bin/cargo"]:
        if Path(candidate).exists():
            return candidate
    for candidate in ["cargo"]:
        try:
            subprocess.run(
                [candidate, "--version"],
                capture_output=True,
                timeout=5,
                check=True,
            )
            return candidate
        except Exception:
            pass
    return None
