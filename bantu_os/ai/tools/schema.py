"""Tool schema for Bantu-OS AI engine.

Defines the canonical tool format that the LLM sees and the engine dispatches.
Each tool carries name, description, parameters, and a handler callable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolParam:
    """A single parameter for a tool."""
    name: str
    description: str
    type: str = "string"          # string | integer | number | boolean | object | array
    required: bool = True
    default: Any = None


@dataclass
class Tool:
    """A callable tool available to the LLM.

    Fields
    ------
    name:
        Unique identifier, lowercase with dots (e.g. "file.read").
    description:
        Human-readable explanation of what the tool does.
    params:
        List of ToolParam objects describing each parameter.
    handler:
        Sync or async callable that accepts **kwargs matching params.
    """
    name: str
    description: str
    params: List[ToolParam] = field(default_factory=list)
    handler: Optional[Callable[..., Any]] = None

    # ------------------------------------------------------------------
    # LLM-friendly serialisation (OpenAI function-calling style)
    # ------------------------------------------------------------------
    def to_function_schema(self) -> Dict[str, Any]:
        """Return an OpenAI-style function-calling schema for this tool."""
        properties: Dict[str, Any] = {}
        required: List[str] = []

        for p in self.params:
            type_map = {
                "string": "string",
                "integer": "integer",
                "number": "number",
                "boolean": "boolean",
                "object": "object",
                "array": "array",
            }
            properties[p.name] = {
                "type": type_map.get(p.type, "string"),
                "description": p.description,
            }
            if p.default is None and p.required:
                required.append(p.name)
            elif p.default is not None and not p.required:
                pass  # optional, leave out of required

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


# ------------------------------------------------------------------
# Built-in tool definitions (schema only — handlers wired in engine.py)
# ------------------------------------------------------------------
BUILTIN_TOOLS: List[Tool] = [
    Tool(
        name="read_file",
        description="Read the full text content of a file. Use this when you need to inspect source code, configs, or documents.",
        params=[
            ToolParam(name="path", description="Absolute path to the file to read.", type="string"),
        ],
    ),
    Tool(
        name="write_file",
        description="Write or overwrite a text file with the given content. Creates parent directories if needed.",
        params=[
            ToolParam(name="path", description="Absolute path of the file to write.", type="string"),
            ToolParam(name="content", description="The text content to write into the file.", type="string"),
        ],
    ),
    Tool(
        name="list_files",
        description="List files and directories at the given path. Defaults to '.' (repo root) if not specified.",
        params=[
            ToolParam(name="path", description="Directory path to list.", type="string", required=False, default="."),
        ],
    ),
    Tool(
        name="run_command",
        description="Execute a shell command and return its stdout/stderr. Use sparingly — prefer built-in tools first.",
        params=[
            ToolParam(name="command", description="The shell command to execute.", type="string"),
        ],
    ),
    Tool(
        name="search_web",
        description="Search the web for information on a given query and return concise results.",
        params=[
            ToolParam(name="query", description="The search query.", type="string"),
            ToolParam(name="time_range", description="Time range: 'day', 'week', 'month', 'year', or 'anytime'.", type="string", required=False, default="anytime"),
        ],
    ),
    Tool(
        name="send_message",
        description="Send a message to a user or channel. Requires recipient and message body.",
        params=[
            ToolParam(name="recipient", description="Recipient identifier (username, email, or channel).", type="string"),
            ToolParam(name="body", description="The message content to send.", type="string"),
        ],
    ),
]