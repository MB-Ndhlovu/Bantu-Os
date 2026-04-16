# Tool Interface — Bantu-OS Kernel

## Overview

Bantu-OS exposes tools through a dual-layer system:

1. **Tool Registry** — a `dict[str, Callable]` registered on `Kernel`
2. **Tool Executor** — a dedicated class that dispatches named tools with JSON args

Tools are plain Python callables. Both sync and async callables are supported.

---

## Tool Registration

### `Kernel.register_tool(name, fn)`

Register a callable tool that `Kernel` can invoke by name.

```python
kernel = Kernel()
kernel.register_tool("echo", lambda value: value)
kernel.register_tool("add", lambda a, b: a + b)
```

---

## Tool Invocation

### `Kernel.use_tool(name, **kwargs)` — sync

```python
result = kernel.use_tool("echo", value="ping")
```

Raises `KeyError` if the tool is not registered. Does **not** await async callables.

---

### `Kernel.use_tool_async(name, **kwargs)` — async

```python
result = await kernel.use_tool_async("echo", value="ping")
```

Detects whether the registered callable is async and awaits it accordingly.
Raises `KeyError` if the tool is not registered.

---

## Batch Execution

### `Kernel.run_tool_calls(calls)` — async

Executes a list of tool calls and returns outcomes.

**Parameter:** `calls: List[Dict[str, Any]]`  
Each dict requires:
- `name: str` — tool identifier
- `args: Dict[str, Any]` — keyword arguments (optional, defaults to `{}`)

**Returns:** `List[Dict[str, Any]]` — parallel list of outcomes

Success:
```json
{ "name": "echo", "result": "pong" }
```

Error:
```json
{ "name": "nonexistent", "error": "Tool not found: nonexistent" }
```

**Example:**
```python
calls = [
    {"name": "echo", "args": {"value": "ping"}},
    {"name": "add",   "args": {"a": 2, "b": 3}}
]
outcomes = await kernel.run_tool_calls(calls)
# [{ "name": "echo", "result": "ping" }, { "name": "add", "result": 5 }]
```

---

## JSON Tool Call Format (external callers)

When an external system (e.g., an LLM agent, an API consumer) dispatches a tool call,
use this canonical JSON structure:

```json
{
  "name": "tool_name",
  "args": {
    "key": "value"
  }
}
```

Example using the shell:

```python
import json
from bantu_os.core.kernel.kernel import Kernel

kernel = Kernel()
kernel.register_tool("echo", lambda value: value)

# Direct call
result = kernel.use_tool("echo", value="hello")

# Via batch API
outcomes = kernel.run_tool_calls([
    {"name": "echo", "args": {"value": "world"}}
])
```

---

## Registering Tools at Construction

You can pass a `tools` dict to `Kernel.__init__`:

```python
def my_echo(value: str) -> str:
    return f"echo: {value}"

kernel = Kernel(tools={"echo": my_echo})
assert kernel.use_tool("echo", value="test") == "echo: test"
```

---

## Built-in Agent Tools

The `bantu_os/agents/tools/` directory contains ready-made tool modules:

| Module | Purpose |
|--------|---------|
| `browser.py` | Web browsing and page interaction |
| `calculator.py` | Arithmetic and math evaluation |
| `file_manager.py` | File-level read/write operations |
| `filesystem.py` | Path-level filesystem operations |
| `scheduler.py` | Calendar and scheduling tasks |
| `web_search.py` | Web search queries |

These are consumed by agent classes (e.g., `SchedulingAgent`, `TaskManager`).

---

## Extending the Interface

To add a new tool:

1. Write the callable (sync or async)
2. Register it: `kernel.register_tool("my_tool", my_fn)`
3. Call it: `kernel.use_tool_async("my_tool", **kwargs)` or via `run_tool_calls([...])`

For async tools that return `Coroutine`, `use_tool_async` and `run_tool_calls` both detect and await automatically.