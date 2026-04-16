"""
ToolExecutor - Dispatches named tools with JSON-serializable arguments.

Provides a structured executor layer on top of Bantu-OS's tool registry.
Works with any dict-of-callable registry (e.g. Kernel.tools).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Dispatches named tools with JSON args.

    Does not own the tool registry — it receives a registry dict at
    construction and operates on it directly.

    Example::

        executor = ToolExecutor(registry={
            "echo": lambda value: value,
            "add":  lambda a, b: a + b,
        })

        result = executor.execute("echo", {"value": "ping"})
        # -> {"success": true, "result": "ping"}
    """

    def __init__(
        self,
        registry: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.registry: Dict[str, Any] = registry or {}

    # -------------------------------------------------------------------------
    # Registry management
    # -------------------------------------------------------------------------

    def register(self, name: str, fn: Any) -> None:
        """Register a callable under ``name``."""
        self.registry[name] = fn

    def unregister(self, name: str) -> bool:
        """Remove a tool by name. Returns True if it existed."""
        return self.registry.pop(name, None) is not None

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    def execute(self, name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dispatch a tool call synchronously.

        Args:
            name: Tool identifier in the registry.
            args: Keyword arguments for the tool (default `{}`).

        Returns:
            A dict with either ``"result"`` or ``"error"`` under key ``"success"``::

                {"success": True,  "result": <return value>}
                {"success": False, "error":  <exception message>}
        """
        if name not in self.registry:
            return {"success": False, "error": f"Tool not found: {name}"}

        kwargs = args or {}
        try:
            raw = self.registry[name](**kwargs)
            # Await coroutines inline (non-async caller context)
            if hasattr(raw, "__await__"):
                # Fall back to sync resolution; note that truly async tools
                # should be called via execute_async from an async context.
                import asyncio
                result = asyncio.get_event_loop().run_until_complete(raw)
            else:
                result = raw
            return {"success": True, "result": result}
        except Exception as exc:  # noqa: BLE001
            logger.exception("ToolExecutor.execute(%s) failed", name)
            return {"success": False, "error": str(exc)}

    async def execute_async(
        self, name: str, args: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Dispatch a tool call, awaiting if the tool is async.

        Args:
            name: Tool identifier in the registry.
            args: Keyword arguments for the tool (default `{}`).

        Returns:
            ``{"success": True, "result": <value>}`` or
            ``{"success": False, "error": <message>}``
        """
        if name not in self.registry:
            return {"success": False, "error": f"Tool not found: {name}"}

        kwargs = args or {}
        try:
            raw = self.registry[name](**kwargs)
            if hasattr(raw, "__await__"):
                result = await raw
            else:
                result = raw
            return {"success": True, "result": result}
        except Exception as exc:  # noqa: BLE001
            logger.exception("ToolExecutor.execute_async(%s) failed", name)
            return {"success": False, "error": str(exc)}

    # -------------------------------------------------------------------------
    # Batch dispatch
    # -------------------------------------------------------------------------

    async def dispatch_batch(
        self, calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute a list of tool calls.

        ``calls`` is a list of dicts with required key ``name`` and
        optional key ``args`` (a dict of keyword arguments)::

            [
                {"name": "echo", "args": {"value": "ping"}},
                {"name": "add",  "args": {"a": 1, "b": 2}}
            ]

        Returns a parallel list of outcome dicts::

            [
                {"name": "echo", "success": True,  "result": "ping"},
                {"name": "add",  "success": True,  "result": 3}
            ]

        Each entry always contains ``"name"`` and ``"success"``.
        On failure, ``"error"`` is present instead of ``"result"``.
        """
        outcomes = []
        for call in calls:
            name = call.get("name", "")
            args = call.get("args", {})
            outcome = await self.execute_async(name, args)
            outcome["name"] = name
            outcomes.append(outcome)
        return outcomes

    # -------------------------------------------------------------------------
    # JSON helpers
    # -------------------------------------------------------------------------

    def execute_json(self, payload: str | bytes | Dict[str, Any]) -> Dict[str, Any]:
        """Parse a JSON tool call and execute it.

        Accepts a JSON string/bytes or a pre-parsed dict::

            executor.execute_json('{"name": "echo", "args": {"value": "hi"}}')
            executor.execute_json({"name": "echo", "args": {"value": "hi"}})

        Returns the same dict as ``execute()``.
        """
        if isinstance(payload, (str, bytes)):
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError as exc:
                return {"success": False, "error": f"Invalid JSON: {exc}"}
        else:
            parsed = payload

        name = parsed.get("name", "")
        args = parsed.get("args", {})
        return self.execute(name, args)

    async def dispatch_batch_json(
        self, payload: str | bytes | List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Parse a JSON array of tool calls and dispatch them all.

        Input can be a JSON-encoded string/bytes or a plain list of dicts::

            executor.dispatch_batch_json('[{"name":"echo","args":{"v":1}}]')
        """
        if isinstance(payload, (str, bytes)):
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError as exc:
                return [{"success": False, "error": f"Invalid JSON: {exc}"}]
        else:
            parsed = payload

        if not isinstance(parsed, list):
            return [{"success": False, "error": "Expected a list of tool calls"}]

        return await self.dispatch_batch(parsed)