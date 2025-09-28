"""
Module entrypoint to launch the Bantu OS CLI.
Run with: python -m bantu_os
"""
from bantu_os.interface.cli.shell import run_shell
from bantu_os.interface.cli.commands import show_version, show_status

def main() -> None:
    commands = {
        'version': show_version,
        'status': show_status,
    }
    run_shell(commands)

if __name__ == "__main__":
    main()
