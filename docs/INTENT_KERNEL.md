# Bantu-OS Intent Kernel

The Intent Kernel replaces the command interface with goals. The user expresses
what they want; the kernel plans it, executes it, monitors progress, retries on
failure, gates destructive actions, and renders a readable summary.

This document is the companion to `bantu_os_intent_kernel_spec.docx` and the
code under `bantu_os/core/intent/`. It captures the architecture, the protocol,
and the public API the rest of the system depends on.

## Why this is different

| Property | Conventional AI shell | Bantu-OS Intent Kernel |
|----------|-----------------------|-------------------------|
| User input | Commands + flags | Natural-language goals |
| Planning | One tool at a time | LLM-composed goal tree |
| Execution | Manual, step-by-step | Autonomous, depth-first |
| Failure recovery | User retries | RetryEngine replans with error context |
| Destructive ops | Either blocked or blind | Confirmation gate with per-session memory |
| Output | Raw tool logs | Plain-English goal outcomes |

## Module map

All new code lives under `bantu_os/core/intent/`. Nothing outside this
directory changes except the socket protocol and the Rust shell's AI routing.

```
bantu_os/core/intent/
  __init__.py
  intent_kernel.py     # Main entry point: IntentKernel class
  goal_planner.py      # LLM-powered goal decomposition (Pydantic-validated)
  goal_tree.py         # GoalTree, GoalNode, GoalStatus data structures
  execution_monitor.py # Watches running tasks, detects failures, emits events
  retry_engine.py      # Re-plans failed sub-tasks with context
  intent_renderer.py   # Formats goal tree progress for the user
  confirmation_gate.py # Holds destructive actions for user approval
```

## Data flow

1. The user types a goal in the Rust shell: `ai on`, then
   "get my project ready to deploy".
2. The shell sends `{"cmd": "intent", "text": "..."}` to the Python kernel.
3. `IntentKernel.receive()` calls `GoalPlanner.decompose(text, context)`.
4. `GoalPlanner` calls the LLM with a planning prompt and validates the JSON
   response with Pydantic (up to 3 attempts).
5. The plan is converted into a `GoalTree` and stored in memory via ChromaDB.
6. `IntentKernel.execute()` walks the tree depth-first. For each leaf, it
   calls `AgentManager._execute_tool_call()`.
7. `ExecutionMonitor` watches each running task. On failure,
   `RetryEngine.replan()` produces an alternative plan, up to `max_retries`.
8. For destructive nodes, `ConfirmationGate` pauses execution and asks the
   caller (via the `ConfirmationResolver`) to approve / skip / abort / explain.
9. On completion, the kernel marks the root goal `DONE` and the
   `IntentRenderer` produces a tree summary.

## Public API

### `IntentKernel.receive(text, context=None, resolver=None) -> dict`

Single-shot request/response. Returns:

- `{"ok": true, "type": "goal_complete", "summary": str, "tree": {...}}` on success
- `{"ok": true, "type": "clarification_needed", "question": str, "tree": {...}}`
  when the planner asked the user for more info
- `{"ok": false, "error": str, "type": "plan_failed" | "goal_failed"}` on failure

### `IntentKernel.receive_streaming(text, context=None, resolver=None) -> AsyncIterator[dict]`

Yields frames as the goal progresses:

- `{"type": "goal_update", "tree": {...}, "message": str, "awaiting_confirmation": bool}`
- `{"type": "clarification_needed", ...}`
- `{"type": "confirmation_required", "step_id": str, "description": str,
   "impact": str, "options": ["approve", "skip", "abort", "explain"]}`
- `{"type": "goal_complete", ...}` (final)
- `{"type": "goal_failed", "error": str, "tree": {...}}` (final)

## Socket protocol additions

Two new message types ride alongside the existing JSON line protocol.

### Shell → Kernel: intent submission

```json
{"cmd": "intent", "text": "get my project ready to deploy", "stream": true}
```

Set `stream: true` to receive frames as the goal progresses; otherwise the
server returns a single `goal_complete` frame after execution.

### Kernel → Shell: streaming update

```json
{"ok": true, "type": "goal_update", "tree": {...}, "message": "Running tests...",
 "awaiting_confirmation": false}
```

### Kernel → Shell: confirmation request

```json
{"ok": true, "type": "confirmation_required", "step_id": "abc123",
 "description": "Build Docker image", "impact": "Builds a new Docker image (~2 min)",
 "options": ["approve", "skip", "abort", "explain"]}
```

### Shell → Kernel: confirmation reply

```json
{"cmd": "confirm", "step_id": "abc123", "decision": "approve"}
```

`decision` must be one of `approve` / `skip` / `abort` / `explain`. The
server resolves the pending future and execution continues.

## Shell UX (Layer 2)

When `ai on` is active, every line is forwarded to the intent kernel. The
shell renders:

- `clarification_needed` → print the clarifying question.
- `goal_complete` → print the summary.
- `confirmation_required` → print the prompt, read a single keystroke
  (`Y`/`S`/`A`/`?`), and send the `confirm` reply on the same socket.

## Renderer rules

- No tool names, file paths, or command strings in default output.
- No error stack traces — translate to plain English.
- Progress is reported as goal-level outcomes, not raw exit codes.
- Timing is shown only for steps that take longer than 5 seconds.
- A `--verbose` flag exposes raw tool output for developers.

## Test coverage

- `tests/intent/test_goal_tree.py` — dataclass round-trip, status values
- `tests/intent/test_goal_planner.py` — LLM planning, validation, unknown tools
- `tests/intent/test_intent_kernel.py` — happy path + direct agent fallback
- `tests/kernel/test_socket_server.py` — added two integration tests:
  intent streaming frames and confirmation round-trip

## Status

- ✅ Phase 1: core intent loop (planning + execution + depth-first walk)
- ✅ Phase 2: retry engine + confirmation gate
- ✅ Phase 3: streaming renderer + memory integration
- See `bantu_os_intent_kernel_spec.docx` for the full design.
