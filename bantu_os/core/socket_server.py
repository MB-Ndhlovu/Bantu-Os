"""
Unix socket server for Bantu-OS shell-to-kernel bridge.
Receives JSON commands from the Rust shell and routes them to the Kernel.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
from pathlib import Path
from typing import Optional

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from bantu_os.core.kernel import Kernel


class SocketServer:
    """Async Unix domain socket server that bridges Rust shell to the Python Kernel."""

    def __init__(
        self,
        socket_path: str = "/tmp/bantu.sock",
        provider: str = "openrouter",
        model: str = "deepseek-ai/deepseek-chat-v3",
        api_key: str = "",
    ):
        self.socket_path = socket_path
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self._kernel: Optional[Kernel] = None
        self._server: Optional[asyncio.Server] = None
        self._shutdown_event = asyncio.Event()

    def _get_kernel(self) -> Kernel:
        """Lazily create a Kernel instance."""
        if self._kernel is None:
            self._kernel = Kernel(
                provider=self.provider,
                provider_model=self.model,
                api_key=self.api_key,
            )
        return self._kernel

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a single client connection — read JSON, process, respond."""
        try:
            # Read one line of JSON
            line = await reader.readline()
            if not line:
                return

            line = line.strip()
            if not line:
                return

            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                resp = json.dumps({"ok": False, "error": f"Invalid JSON: {e}"})
                writer.write(resp.encode() + b"\n")
                await writer.drain()
                return

            cmd = request.get("cmd")
            text = request.get("text", "")

            if cmd == "ai":
                try:
                    result = await self._get_kernel().process_input(text)
                    resp = json.dumps({"ok": True, "result": result})
                except Exception as e:
                    resp = json.dumps({"ok": False, "error": str(e)})
            else:
                resp = json.dumps({"ok": False, "error": f"Unknown cmd: {cmd}"})

            writer.write(resp.encode() + b"\n")
            await writer.drain()

        except Exception as e:
            try:
                resp = json.dumps({"ok": False, "error": str(e)})
                writer.write(resp.encode() + b"\n")
                await writer.drain()
            except Exception:
                pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def run(self):
        """Start the server and run until shutdown is signalled."""
        loop = asyncio.get_running_loop()

        # Remove stale socket
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        self._server = await loop.create_unix_server(
            lambda: asyncio.StreamReader(),  # factory, asyncio handles protocol
            path=self.socket_path,
        )

        # Actually we need the full server object — use create_unix_server properly
        # create_unix_server returns a server directly
        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=self.socket_path,
        )

        # Make socket writable by all
        os.chmod(self.socket_path, 0o666)

        print(f"Socket server listening on {self.socket_path}", flush=True)

        self._shutdown_event.clear()
        await self._shutdown_event.wait()

    async def shutdown(self):
        """Initiate graceful shutdown."""
        self._shutdown_event.set()
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except FileNotFoundError:
                pass
        print("Socket server stopped.", flush=True)


async def main():
    import argparse

    parser = argparse.ArgumentParser(description='Bantu-OS Socket Server')
    parser.add_argument('--socket', default='/tmp/bantu.sock', help='Socket path')
    parser.add_argument('--provider', default='openrouter',
                        help='LLM provider (openrouter or openai)')
    parser.add_argument('--model', default='deepseek-ai/deepseek-chat-v3',
                        help='Model name for the provider')
    parser.add_argument('--api-key', default='',
                        help='API key (or set OPENROUTER_API_KEY env var)')
    args = parser.parse_args()

    server = SocketServer(
        socket_path=args.socket,
        provider=args.provider,
        model=args.model,
        api_key=args.api_key,
    )

    loop = asyncio.get_running_loop()

    def shutdown_signal():
        asyncio.create_task(server.shutdown())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_signal)

    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
