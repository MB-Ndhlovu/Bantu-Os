"""bantu-admin CLI — manage Bantu-OS services via the admin socket."""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import sys
from pathlib import Path
from typing import Any

ADMIN_SOCK = Path("/tmp/bantu-admin.sock")


def cmd(sock_path: str, payload: dict[str, Any]) -> dict[str, Any]:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.settimeout(10.0)
        sock.connect(sock_path)
        data = json.dumps(payload).encode() + b"\n"
        sock.sendall(data)
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            try:
                return json.loads(response.decode())
            except json.JSONDecodeError:
                continue
    finally:
        sock.close()


async def main() -> int:
    parser = argparse.ArgumentParser(
        prog="bantu-admin", description="Bantu-OS service manager"
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Overall service manager status")
    sub.add_parser("list", help="List managed services and their PIDs")
    p_start = sub.add_parser("start", help="Start a service")
    p_start.add_argument("name", help="Service name (e.g. kernel, shell)")
    p_stop = sub.add_parser("stop", help="Stop a service")
    p_stop.add_argument("name", help="Service name")
    p_stop.add_argument(
        "--force", action="store_true", help="SIGKILL instead of SIGTERM"
    )
    p_restart = sub.add_parser("restart", help="Restart a service")
    p_restart.add_argument("name", help="Service name")
    p_logs = sub.add_parser("logs", help="Tail the log file for a service")
    p_logs.add_argument("name", help="Service name")
    p_logs.add_argument("--lines", "-n", type=int, default=20, help="Number of lines")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "status":
        result = cmd(str(ADMIN_SOCK), {"cmd": "status"})
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1

    if args.command == "list":
        result = cmd(str(ADMIN_SOCK), {"cmd": "list"})
        if result.get("ok"):
            services = result.get("result", {}).get("services", [])
            for s in services:
                pid = s.get("pid") or "stopped"
                print(f"{s['name']:12}  pid={pid}")
        else:
            print(f"Error: {result.get('error')}", file=sys.stderr)
            return 1
        return 0

    if args.command == "start":
        result = cmd(str(ADMIN_SOCK), {"cmd": "start", "name": args.name})
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1

    if args.command == "stop":
        result = cmd(
            str(ADMIN_SOCK), {"cmd": "stop", "name": args.name, "force": args.force}
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1

    if args.command == "restart":
        result = cmd(str(ADMIN_SOCK), {"cmd": "restart", "name": args.name})
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1

    if args.command == "logs":
        result = cmd(
            str(ADMIN_SOCK), {"cmd": "logs", "name": args.name, "lines": args.lines}
        )
        if result.get("ok"):
            print(result["result"]["log"])
        else:
            print(f"Error: {result.get('error')}", file=sys.stderr)
            return 1
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
