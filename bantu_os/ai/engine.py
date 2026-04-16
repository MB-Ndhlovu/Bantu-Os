"""AI Engine — orchestrates LLM calls, tool dispatch, and result handling."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from bantu_os.core.kernel.llm_manager import LLMManager
from bantu_os.core.kernel.providers.base import ChatMessage, GenerateResult

from .tools.schema import Tool, BUILTIN_TOOLS


# ------------------------------------------------------------------
# Tool handlers — wired to the built-in tool schema
# ------------------------------------------------------------------
def _read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def _write_file(path: str, content: str) -> str:
    import os
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return f"Wrote {len(content)} bytes to {path}"


def _list_files(path: str = ".") -> List[str]:
    import os
    return sorted(os.listdir(path))


def _run_command(command: str) -> Dict[str, Any]:
    import subprocess
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=30
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


async def _search_web(query: str, time_range: str = "anytime") -> Dict[str, Any]:
    """Placeholder web search — replace with real search client."""
    return {"query": query, "time_range": time_range, "results": []}


def _send_message(recipient: str, body: str) -> Dict[str, Any]:
    return {"recipient": recipient, "body": body, "sent": True}


BUILTIN_HANDLERS: Dict[str, Any] = {
    "read_file": _read_file,
    "write_file": _write_file,
    "list_files": _list_files,
    "run_command": _run_command,
    "search_web": _search_web,
    "send_message": _send_message,
}


# ------------------------------------------------------------------
# Main engine
# ------------------------------------------------------------------
class AIEngine:
    """Main AI engine.

    Parameters
    ----------
    llm_manager:
        Pre-configured LLMManager instance (from bantu_os.core.kernel).
    system_prompt:
        Static system prompt injected before every user turn.
    tools:
        List of Tool objects describing available tools. Defaults to BUILTIN_TOOLS.
    max_iterations:
        Max tool-call loops before returning. Defaults to 10.
    """

    def __init__(
        self,
        llm_manager: LLMManager,
        system_prompt: str = "You are a helpful AI assistant.",
        tools: Optional[List[Tool]] = None,
        max_iterations: int = 10,
    ) -> None:
        self.llm = llm_manager
        self.system_prompt = system_prompt
        self.tools: List[Tool] = tools if tools is not None else BUILTIN_TOOLS
        self.max_iterations = max_iterations

        # Build name → Tool lookup
        self._tool_map: Dict[str, Tool] = {t.name: t for t in self.tools}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def run(
        self,
        user_input: str,
        memory_context: Optional[List[ChatMessage]] = None,
    ) -> str:
        """Run the full think-act loop and return the final text response.

        Parameters
        ----------
        user_input:
            The raw user message.
        memory_context:
            Optional list of prior ChatMessages (e.g. from a session store)
            to pre-load into the conversation.
        """
        messages: List[ChatMessage] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        if memory_context:
            messages.extend(memory_context)
        messages.append({"role": "user", "content": user_input})

        for _ in range(self.max_iterations):
            result = await self._generate_with_tools(messages)
            if not result.continuation:
                return result.text

            # result.tool_calls are appended as assistant messages
            messages.extend(result.new_messages)

        # Exceeded max iterations
        return (
            "I apologies for the inconvenience — I seem to be caught in a loop. "
            "Could you please rephrase or break that down?"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_tool_system_message(self) -> ChatMessage:
        schemas = [t.to_function_schema() for t in self.tools]
        tool_definitions = json.dumps(schemas, indent=2)
        return {
            "role": "system",
            "content": (
                "You have access to the following tools. "
                "To call a tool, respond with a JSON object of the form:\n"
                '{"name": "<tool_name>", "arguments": {"param": "value"}}\n\n'
                f"Available tools:\n{tool_definitions}"
            ),
        }

    async def _generate_with_tools(
        self, messages: List[ChatMessage]
    ) -> _GenerateResult:
        """Send messages to LLM, extract tool calls, dispatch, and return."""
        tool_system_msg = self._build_tool_system_message()

        # Inject tool definitions at the front of the non-system tail
        # by cloning the message list
        injection_done = False
        enriched: List[ChatMessage] = []
        for m in messages:
            enriched.append(m)
            if m["role"] == "user" and not injection_done:
                enriched.append(tool_system_msg)
                injection_done = True

        response: GenerateResult = await self.llm.generate(
            messages=enriched,
            temperature=0.7,
        )
        text = response.get("text", "")
        raw = response.get("raw") or {}

        # Parse tool calls from raw response
        tool_calls = self._extract_tool_calls(raw, text)

        if not tool_calls:
            return _GenerateResult(text=text, continuation=False, new_messages=[])

        # Dispatch each tool call
        results: List[Dict[str, Any]] = []
        assistant_msgs: List[ChatMessage] = []

        for call in tool_calls:
            name = call["name"]
            args = call.get("arguments", {})
            tool_result = self._dispatch_tool(name, args)
            results.append({"tool": name, "result": tool_result})

            # Build the assistant message that would have triggered this
            assistant_msgs.append({
                "role": "assistant",
                "content": text[:500] if text else None,
                "tool_calls": [
                    {"id": call.get("id", ""), "name": name, "arguments": json.dumps(args)}
                ],
            })

            # Append the tool result as a tool message
            messages.append({
                "role": "tool",
                "content": json.dumps(tool_result),
                "name": name,
            })

        return _GenerateResult(
            text=text,
            continuation=True,
            new_messages=assistant_msgs,
        )

    def _extract_tool_calls(
        self, raw: Any, text: str
    ) -> List[Dict[str, Any]]:
        """Extract tool calls from provider-specific raw response or text fallback."""
        calls: List[Dict[str, Any]] = []

        # Try OpenAI-style tool_calls array
        if isinstance(raw, dict):
            tc = raw.get("tool_calls") or raw.get("function_call")
            if tc:
                if isinstance(tc, list):
                    for item in tc:
                        calls.append(self._normalise_call(item))
                elif isinstance(tc, dict):
                    calls.append(self._normalise_call(tc))

        # Regex fallback on text (handles annotated code blocks)
        if not calls and text:
            calls = self._extract_from_text(text)

        return calls

    def _normalise_call(self, raw_call: Any) -> Dict[str, Any]:
        """Normalise diverse provider call formats to a consistent dict."""
        if isinstance(raw_call, dict):
            name = (
                raw_call.get("name")
                or raw_call.get("function", {}).get("name")
                or raw_call.get("function_name")
                or ""
            )
            args_raw = (
                raw_call.get("arguments")
                or raw_call.get("function", {}).get("arguments")
                or "{}"
            )
            args = args_raw
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"_raw": args}
        else:
            name = str(raw_call)
            args = {}
        return {"name": name, "arguments": args, "id": raw_call.get("id", "") if isinstance(raw_call, dict) else ""}

    def _extract_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract tool calls from plain text responses (JSON in code blocks)."""
        calls: List[Dict[str, Any]] = []
        pattern = re.compile(
            r'```(?:json)?\s*(\{"name"\s*:\s*"([^"]+)".*?})\s*```',
            re.DOTALL,
        )
        for match in pattern.finditer(text):
            try:
                call = json.loads(match.group(1))
                calls.append(call)
            except json.JSONDecodeError:
                pass
        return calls

    def _dispatch_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name and return a JSON-serialisable result dict."""
        if name not in self._tool_map:
            return {"success": False, "error": f"Unknown tool: {name}"}

        tool = self._tool_map[name]
        handler = BUILTIN_HANDLERS.get(name)

        if handler is None:
            return {"success": False, "error": f"No handler for tool: {name}"}

        try:
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                result = asyncio.run(handler(**args))
            else:
                result = handler(**args)
            return {"success": True, "result": result}
        except TypeError as e:
            return {"success": False, "error": f"Bad arguments for {name}: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ------------------------------------------------------------------
# Internal result carrier
# ------------------------------------------------------------------
class _GenerateResult:
    __slots__ = ("text", "continuation", "new_messages")

    def __init__(
        self,
        text: str,
        continuation: bool,
        new_messages: List[ChatMessage],
    ) -> None:
        self.text = text
        self.continuation = continuation
        self.new_messages = new_messages