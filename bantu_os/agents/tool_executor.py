#!/usr/bin/env python3
"""Tool Executor - dispatches named tools with JSON args."""

from __future__ import annotations
import json
from typing import Any, Dict, Optional, Callable


class ToolExecutor:
    """Dispatches tool calls to registered Python service functions."""

    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., Any]] = {}

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        self._tools[name] = fn

    def execute(self, tool: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = args or {}
        if tool not in self._tools:
            return {"success": False, "error": f"Unknown tool: {tool}"}
        try:
            result = self._tools[tool](**args)
            return {"success": True, "result": result}
        except TypeError as e:
            return {"success": False, "error": f"Bad args for {tool}: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())


# Built-in tools
def tool_file_read(path: str) -> str:
    with open(path, "r") as f:
        return f.read()

def tool_file_write(path: str, content: str) -> str:
    with open(path, "w") as f:
        f.write(content)
    return f"Wrote {len(content)} bytes to {path}"

def tool_file_list(path: str = ".") -> list[str]:
    import os
    return sorted(os.listdir(path))

def tool_process_spawn(cmd: str) -> dict:
    import subprocess, uuid
    pid = subprocess.Popen(cmd, shell=True).pid
    return {"pid": pid, "id": str(uuid.uuid4())[:8]}

def tool_process_list() -> list[dict]:
    import os
    return [{"pid": p} for p in range(1, 32768) if os.path.exists(f"/proc/{p}")]

def tool_memory_store(text: str, meta: Optional[dict] = None) -> str:
    return f"Stored: {text[:50]}..."

def tool_network_get(url: str) -> dict:
    import urllib.request, json
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return {"status": 200, "body": r.read().decode()[:500]}
    except Exception as e:
        return {"status": 0, "error": str(e)}

# Default executor instance
_executor = ToolExecutor()
_executor.register("file.read", tool_file_read)
_executor.register("file.write", tool_file_write)
_executor.register("file.list", tool_file_list)
_executor.register("process.spawn", tool_process_spawn)
_executor.register("process.list", tool_process_list)
_executor.register("memory.store", tool_memory_store)
_executor.register("network.get", tool_network_get)

dispatch = _executor.execute
list_tools = _executor.list_tools
