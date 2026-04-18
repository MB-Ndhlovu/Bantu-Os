# Bantu-OS AI Shell

## Overview

The Bantu-OS shell (Layer 2) replaces bash as the primary interface. It provides a natural language REPL that parses commands and dispatches to system tools.

## Architecture

```
┌─────────────────────────────────────┐
│           User Input                │
│    "list files in /home"           │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│          REPL Loop                  │
│   Read → Parse → Execute → Loop    │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│         Parser (parser.rs)          │
│   Natural language → ToolCall      │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│      Tool Registry (tools.rs)      │
│   ToolCall → System Command        │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│        Python AI Engine             │
│      (IPC: Unix socket / TCP)      │
└─────────────────────────────────────┘
```

## Components

### main.rs

- REPL loop (stdin/stdout, no external line editor dependency)
- Signal handling (Ctrl+C graceful exit)
- Dual mode: shell commands and AI mode (`ai <message>`)
- Input → `handle_shell_input()` or `handle_ai_input()` → output flow

### parser.rs

Converts natural language to structured `ToolCall`:

```rust
pub struct ToolCall {
    pub tool: String,     // e.g., "ls", "cat", "ps"
    pub args: Vec<String>,
    pub raw: String,      // original input
}
```

### tools.rs

`ToolRegistry` manages available system tools. Default tools: `ls`, `cat`, `ps`, `pwd`, `whoami`, `cd`, `mkdir`, `rm`, `cp`, `mv`, `grep`, `kill`, `write`, `run`.

## Adding New Tools

1. Add to `tools.rs` `register_default_tools()`:

```rust
Tool {
    name: "mytool".to_string(),
    description: "Does something".to_string(),
    args: vec!["arg1".to_string()],
}
```

2. Add execution handler:

```rust
fn execute_mytool(&self, args: &[String]) -> Result<String, ToolError> {
    // implementation
}
```

3. Add match arm in `execute()`:

```rust
"mytool" => self.execute_mytool(args),
```

## IPC with Python AI Engine

The shell connects to the Python kernel via Unix socket (primary) or TCP (future multi-client):

**Unix Socket** (production):
```rust
let stream = std::os::unix::net::UnixStream::connect("/tmp/bantu.sock");
```

**TCP** (multi-client / telnet use):
```rust
// Python kernel listens on 127.0.0.1:18792
```

**AI message protocol** (JSON over socket):

```json
// Shell → Kernel
{"cmd": "ai", "text": "hello"}

// Kernel → Shell (success)
{"ok": true, "result": "Hello! How can I help?"}

// Kernel → Shell (error)
{"ok": false, "error": "error message"}
```

**Tool command protocol**:

```json
// Shell → Kernel
{"cmd": "tool", "tool": "file", "method": "read", "args": {"path": "/tmp/test.txt"}}

// Kernel → Shell
{"ok": true, "result": "file contents"}
```

## Running

```bash
cd shell
cargo build --release
./target/release/bantu
```

## Testing

```bash
cargo test
```
