"""
Bantu-OS CLI Server — connects Rust shell to Python AI engine.
Listens on Unix socket /tmp/bantu.sock for commands from the Rust shell.
"""
from __future__ import annotations

import os
import socket
import threading
import json
from typing import Optional

from bantu_os.core.kernel import Kernel
from bantu_os.ai.service import AIService


class CLIServer:
    def __init__(self, socket_path: str = "/tmp/bantu.sock") -> None:
        self.socket_path = socket_path
        self.running = False
        self.kernel: Optional[Kernel] = None
        self.ai_service: Optional[AIService] = None

    def setup(self) -> None:
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.socket_path)
        self.sock.listen(5)
        os.chmod(self.socket_path, 0o600)

    def start(self, background: bool = True) -> None:
        self.running = True
        if background:
            thread = threading.Thread(target=self._serve, daemon=True)
            thread.start()
        else:
            self._serve()

    def _serve(self) -> None:
        while self.running:
            try:
                conn, _ = self.sock.accept()
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
            except OSError:
                break

    def _handle(self, conn: socket.socket) -> None:
        try:
            data = conn.recv(4096)
            if not data:
                return
            request = json.loads(data.decode())
            response = self.process(request)
            conn.sendall(json.dumps(response).encode())
        except Exception as e:
            conn.sendall(json.dumps({"error": str(e)}).encode())
        finally:
            conn.close()

    def process(self, request: dict) -> dict:
        cmd = request.get("cmd")
        if cmd == "ai":
            text = request.get("text", "")
            result = self.ai_service.chat(text)
            return {"ok": True, "result": result}
        elif cmd == "status":
            return {
                "ok": True,
                "status": "running",
                "ai_ready": self.ai_service is not None,
            }
        elif cmd == "ping":
            return {"ok": True, "pong": True}
        return {"ok": False, "error": f"Unknown command: {cmd}"}

    def stop(self) -> None:
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)


if __name__ == "__main__":
    server = CLIServer()
    server.setup()
    server.ai_service = AIService()
    print("Bantu-OS CLI server running on /tmp/bantu.sock")
    print("Waiting for shell connections...")
    server.start(background=False)
