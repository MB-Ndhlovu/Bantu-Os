#!/usr/bin/env python3
"""bantu-admin: CLI client for the Bantu-OS Service Manager.

Usage:
    bantu-admin status              Show all services
    bantu-admin start <service>     Start a service (kernel|shell)
    bantu-admin stop <service>      Stop a service
    bantu-admin restart <service>   Restart a service
    bantu-admin logs <service>      Show last 100 log lines
    bantu-admin ping                Ping the daemon
    bantu-admin shutdown            Shutdown the daemon
    bantu-admin --help              Show this help

Requires the service_manager daemon to be running.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys

SOCK_PATH = "/tmp/bantu-admin.sock"
TIMEOUT = 5.0


def send_command(cmd: str, arg: str | None = None) -> dict:
    """Send a JSON command to the admin socket and return the response."""
    payload = {"cmd": cmd, "arg": arg}
    if arg:
        payload["arg"] = arg

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect(SOCK_PATH)
        sock.sendall(json.dumps(payload).encode("utf-8") + b"\n")
        sock.shutdown(socket.SHUT_WR)
        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        return json.loads(data.decode("utf-8"))
    except FileNotFoundError:
        return {"ok": False, "error": f"Daemon not running at {SOCK_PATH}"}
    except socket.timeout:
        return {"ok": False, "error": "Daemon timeout"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "Invalid response from daemon"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def print_status(status: dict) -> None:
    """Pretty-print service status."""
    print(f"{'Service':<12} {'PID':<8} {'Running':<10} {'Socket/Log'}")
    print("-" * 60)
    for name, info in status.items():
        pid = info.get("pid", "—")
        running = "🟢 yes" if info.get("running") else "🔴 no"
        socket_info = info.get("socket") or info.get("log", "—")
        print(f"{name:<12} {str(pid):<8} {running:<10} {socket_info}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bantu-admin", description="Bantu-OS Service Manager CLI"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show service status")
    sub.add_parser("ping", help="Ping the daemon")

    start = sub.add_parser("start", help="Start a service")
    start.add_argument("service", choices=["kernel", "shell"], help="Service to start")

    stop = sub.add_parser("stop", help="Stop a service")
    stop.add_argument("service", choices=["kernel", "shell"], help="Service to stop")

    restart = sub.add_parser("restart", help="Restart a service")
    restart.add_argument(
        "service", choices=["kernel", "shell"], help="Service to restart"
    )

    logs = sub.add_parser("logs", help="Show service logs (last 100 lines)")
    logs.add_argument(
        "service", choices=["kernel", "shell"], help="Service whose logs to show"
    )

    sub.add_parser("shutdown", help="Shutdown the daemon")

    user_add = sub.add_parser("user-add", help="Register a new user")
    user_add.add_argument("username", help="Username")
    user_add.add_argument(
        "--api-key", help="Optional API key (auto-generated if omitted)"
    )

    user_rm = sub.add_parser("user-rm", help="Remove a user")
    user_rm.add_argument("username", help="Username to remove")

    sub.add_parser("users", help="List all registered users")

    args = parser.parse_args()

    if args.cmd == "status":
        resp = send_command("status")
        if not resp.get("ok"):
            print(f"Error: {resp.get('error')}", file=sys.stderr)
            sys.exit(1)
        print_status(resp["result"])

    elif args.cmd == "ping":
        resp = send_command("ping")
        if resp.get("ok"):
            print("Daemon is alive")
        else:
            print(f"Error: {resp.get('error')}", file=sys.stderr)
            sys.exit(1)

    elif args.cmd == "logs":
        resp = send_command("logs", args.service)
        if not resp.get("ok"):
            print(f"Error: {resp.get('error')}", file=sys.stderr)
            sys.exit(1)
        print(resp["result"])

    elif args.cmd in ("start", "stop", "restart"):
        resp = send_command(args.cmd, args.service)
        if not resp.get("ok"):
            print(f"Error: {resp.get('error')}", file=sys.stderr)
            sys.exit(1)
        print(resp["result"])

    elif args.cmd == "shutdown":
        resp = send_command("shutdown")
        print(resp.get("result", "Daemon shutdown"))
        sys.exit(0 if resp.get("ok") else 1)

    elif args.cmd == "user-add":
        resp = send_command("user_add", args.username)
        if not resp.get("ok"):
            print(f"Error: {resp.get('error')}", file=sys.stderr)
            sys.exit(1)
        print(resp["result"])

    elif args.cmd == "user-rm":
        resp = send_command("user_rm", args.username)
        if not resp.get("ok"):
            print(f"Error: {resp.get('error')}", file=sys.stderr)
            sys.exit(1)
        print(resp["result"])

    elif args.cmd == "users":
        resp = send_command("users")
        if not resp.get("ok"):
            print(f"Error: {resp.get('error')}", file=sys.stderr)
            sys.exit(1)
        print(resp["result"])


if __name__ == "__main__":
    main()
