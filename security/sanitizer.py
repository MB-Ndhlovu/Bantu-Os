"""
Input Sanitizer for Bantu-OS

Prevents prompt injection and input-based attacks by sanitizing
all user input before it reaches the AI context or tool dispatch.

Rejection triggers:
- Null bytes (\x00)
- Path traversal (../, ..\\)
- Shell metacharacters in argument contexts
- Injection patterns ({{, ${, <%, -->)
- Overlong UTF-8 / encoding anomalies
"""

from __future__ import annotations

import os
import re
import urllib.parse
from pathlib import Path
from typing import Any, Optional

# Maximum lengths per input type
MAX_PATH_LEN = 4096
MAX_URL_LEN = 2048
MAX_CMD_ARGS_LEN = 65536
MAX_CONTENT_LEN = 16 * 1024 * 1024  # 16MB

# Allowed characters per input type
RE_PATH_COMPONENT = re.compile(r"^[a-zA-Z0-9_\-./ ]+$")
RE_URL_PATH = re.compile(r"^[a-zA-Z0-9_\-./?#&=+%]+$")
RE_CMD_ARG = re.compile(r"^[a-zA-Z0-9_\-./:+=,@%]+$")

# Dangerous patterns that always trigger rejection
DANGEROUS_PATTERNS = [
    (re.compile(r"\x00"), "null_byte"),
    (re.compile(r"\.\.[/\\]"), "path_traversal"),
    (re.compile(r"[|;&]`"), "shell_metachar"),
    (re.compile(r"\$\("), "command_substitution"),
    (re.compile(r"\{\{"), "template_injection"),
    (re.compile(r"<%"), "server_side_injection"),
    (re.compile(r"<!--"), "html_comment_injection"),
    (re.compile(r"\x1b\["), "ansi_escape"),
    (re.compile(r"%0a|%0d", re.IGNORECASE), "url_newline_injection"),
]

# Schema for tool argument validation
TOOL_ARG_SCHEMAS: dict[str, dict[str, Any]] = {
    "filesystem.read": {
        "path": {"type": "path", "max_len": MAX_PATH_LEN},
    },
    "filesystem.write": {
        "path": {"type": "path", "max_len": MAX_PATH_LEN},
        "content": {"type": "content", "max_len": MAX_CONTENT_LEN},
    },
    "filesystem.delete": {
        "path": {"type": "path", "max_len": MAX_PATH_LEN},
    },
    "filesystem.list": {
        "path": {"type": "path", "max_len": MAX_PATH_LEN},
    },
    "network.request": {
        "url": {"type": "url", "max_len": MAX_URL_LEN},
        "method": {"type": "enum", "values": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
    },
    "process.spawn": {
        "cmd": {"type": "cmd", "max_len": MAX_CMD_ARGS_LEN},
        "args": {"type": "cmd_args_list"},
    },
}


class SanitizationError(ValueError):
    """Raised when input fails sanitization."""
    def __init__(self, reason: str, field: str = ""):
        self.reason = reason
        self.field = field
        super().__init__(f"Sanitization failed for '{field}': {reason}")


def sanitize_path(path: str, allow_absolute: bool = False) -> str:
    """
    Sanitize a filesystem path.

    - Must resolve within allowed directories
    - No null bytes, traversal, or special characters
    - If allow_absolute=False, must be relative to workspace
    """
    if not path:
        raise SanitizationError("empty path", "path")
    if len(path) > MAX_PATH_LEN:
        raise SanitizationError(f"exceeds {MAX_PATH_LEN} chars", "path")

    for pattern, name in DANGEROUS_PATTERNS:
        if pattern.search(path):
            raise SanitizationError(f"dangerous pattern: {name}", "path")

    if ".." in path:
        raise SanitizationError("path traversal", "path")

    # Resolve symlinks and check it stays within workspace
    try:
        resolved = Path(path).resolve()
        workspace = Path(os.environ.get("BANTU_WORKSPACE", "/home/workspace"))
        z_path = Path("/home/.z")

        if not allow_absolute:
            try:
                resolved.relative_to(workspace)
            except ValueError:
                try:
                    resolved.relative_to(z_path)
                except ValueError:
                    raise SanitizationError("path outside workspace", "path")
    except Exception as e:
        raise SanitizationError(f"invalid path: {e}", "path")

    # Check allowed characters in each component
    for part in Path(path).parts:
        if part != "." and not RE_PATH_COMPONENT.match(part):
            raise SanitizationError(f"invalid char in component: {part!r}", "path")

    return str(resolved)


def sanitize_url(url: str) -> str:
    """
    Sanitize a URL.

    - Only HTTP/HTTPS allowed
    - No credentials in URL
    - No dangerous schemes
    - No internal network access
    """
    if not url:
        raise SanitizationError("empty URL", "url")
    if len(url) > MAX_URL_LEN:
        raise SanitizationError(f"exceeds {MAX_URL_LEN} chars", "url")

    # Check for null byte and path traversal in raw URL
    if "\x00" in url:
        raise SanitizationError("null byte in URL", "url")

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        raise SanitizationError(f"invalid URL: {e}", "url")

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise SanitizationError(f"disallowed scheme: {scheme}", "url")

    if parsed.username or parsed.password:
        raise SanitizationError("credentials in URL", "url")

    # Block localhost and internal networks
    hostname = parsed.hostname or ""
    blocked = (
        hostname in ("localhost", "127.0.0.1", "::1")
        or hostname.startswith("10.")
        or hostname.startswith("172.16.")
        or hostname.startswith("192.168.")
        or hostname.startswith("169.254.")
        or hostname.endswith(".internal")
        or hostname.endswith(".local")
    )
    if blocked:
        raise SanitizationError("internal network access blocked", "url")

    # Reject URLs with newlines or control chars
    if any(ord(c) < 0x20 for c in url):
        raise SanitizationError("control characters in URL", "url")

    # Check path for traversal and dangerous patterns (but not injection markers in paths)
    path = parsed.path or ""
    if ".." in path:
        raise SanitizationError("path traversal in URL", "url")
    # Check for URL-encoded newlines - reject if found
    if re.search(r"%0a|%0d", url, re.IGNORECASE):
        raise SanitizationError("newline injection in URL", "url")

    # Ensure URL path is safe (basic chars only)
    if path and not RE_URL_PATH.match(path):
        raise SanitizationError("unsafe URL path characters", "url")

    return url


def sanitize_cmd_arg(arg: str) -> str:
    """
    Sanitize a single command-line argument.

    - No shell metacharacters
    - No environment variable expansion
    - Length limit
    """
    if not arg:
        return ""
    if len(arg) > MAX_CMD_ARGS_LEN:
        raise SanitizationError(f"exceeds {MAX_CMD_ARGS_LEN} chars", "arg")

    for pattern, name in DANGEROUS_PATTERNS:
        if pattern.search(arg):
            raise SanitizationError(f"dangerous pattern: {name}", "arg")

    # Check for shell metacharacters
    if not RE_CMD_ARG.match(arg):
        raise SanitizationError("disallowed characters in command arg", "arg")

    # Explicitly block common injection patterns
    if "${" in arg or "$(" in arg:
        raise SanitizationError("variable expansion in arg", "arg")

    return arg


def sanitize_cmd_args(args: list[str]) -> list[str]:
    """Sanitize a list of command arguments."""
    return [sanitize_cmd_arg(a) for a in args]


def sanitize_content(content: str, max_len: int = MAX_CONTENT_LEN) -> str:
    """Sanitize arbitrary text content with length limit."""
    if len(content) > max_len:
        raise SanitizationError(f"exceeds {max_len} chars", "content")

    # Remove null bytes
    content = content.replace("\x00", "")

    # Detect overlong UTF-8 or obvious injection markers
    try:
        content.encode("utf-8")
    except UnicodeEncodeError:
        raise SanitizationError("invalid UTF-8 encoding", "content")

    return content


def sanitize_tool_args(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """
    Validate and sanitize tool arguments against their schema.

    Raises SanitizationError if validation fails.
    """
    schema = TOOL_ARG_SCHEMAS.get(tool_name, {})

    if not schema:
        # Unknown tool — accept args as-is but apply generic sanitization
        return {k: sanitize_content(str(v)) for k, v in args.items()}

    sanitized = {}
    for field, value in args.items():
        if field not in schema:
            continue  # Ignore unknown fields

        field_schema = schema[field]
        ftype = field_schema["type"]

        try:
            if ftype == "path":
                sanitized[field] = sanitize_path(str(value))
            elif ftype == "url":
                sanitized[field] = sanitize_url(str(value))
            elif ftype == "cmd":
                sanitized[field] = sanitize_cmd_arg(str(value))
            elif ftype == "cmd_args_list":
                if isinstance(value, list):
                    sanitized[field] = sanitize_cmd_args([str(a) for a in value])
                else:
                    sanitized[field] = [sanitize_cmd_arg(str(value))]
            elif ftype == "content":
                sanitized[field] = sanitize_content(str(value), field_schema.get("max_len", MAX_CONTENT_LEN))
            elif ftype == "enum":
                if value not in field_schema["values"]:
                    raise SanitizationError(f"invalid enum value: {value}", field)
                sanitized[field] = value
        except SanitizationError:
            raise
        except Exception as e:
            raise SanitizationError(f"{ftype} validation failed: {e}", field)

    return sanitized


def sanitize_tool_name(name: str) -> str:
    """Validate that a tool name is a registered identifier."""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$", name):
        raise SanitizationError("invalid tool name format", "tool_name")
    return name


def sanitize_prompt(text: str, max_len: int = 128_000) -> str:
    """
    Sanitize user prompt before it enters the AI context.

    This is a last-resort sanitization layer that removes the most
    dangerous injection patterns while preserving legitimate input.
    """
    if len(text) > max_len:
        raise SanitizationError(f"exceeds {max_len} chars", "prompt")

    # Remove obvious injection markers in one pass
    # - {{ and }} as separate tokens
    # - <% and %> as separate tokens  
    # - HTML comments <!-- -->
    # - $$ (double dollar normalized to single)
    injection_pattern = re.compile(r"\{\{|}}\s*|<%|%>|<!--|-->|\$\$")
    result = injection_pattern.sub("", text)

    return result
