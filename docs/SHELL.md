# Bantu-OS AI Shell

## Overview

The Bantu-OS shell (Layer 2) replaces bash as the primary interface. It provides a natural language REPL that parses commands and dispatches to system tools.

## Architecture

```
┌─────────────────────────────────────┐
│           User Input                │
│    "list files in /home"            │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│          REPL Loop                  │
│   Read → Parse → Execute → Loop    │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│         Parser (parser.rs)          │
│   Natural language → ToolCall       │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│      Tool Registry (tools.rs)      │
│   ToolCall → System Command         │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│        Python AI Engine             │
│      (IPC: Unix socket / stdio)     │
└─────────────────────────────────────┘
```

## Components

### main.rs
- REPL loop using `rustyline` for line editing
- Signal handling (Ctrl+C graceful exit)
- History support (`/tmp/bantu_shell_history`)
- Input → `process_input()` → output flow

### parser.rs
Converts natural language to structured `ToolCall`:
```rust
pub struct ToolCall {
    pub tool: String,    // e.g., "ls", "cat", "ps"
    pub args: Vec<String>,
    pub raw: String,    // original input
}
```

**Natural language mappings:**
- `list`/`ls`/`show` → `ls`
- `read`/`cat`/`view` → `cat`
- `status`/`ps` → `ps`
- `find`/`search`/`grep` → `grep`
- etc.

### tools.rs
`ToolRegistry` manages available system tools:

| Tool | Description | Args |
|------|-------------|------|
| `ls` | List directory | `[path]` |
| `cat` | Display file | `file` |
| `ps` | Processes | - |
| `pwd` | Working dir | - |
| `whoami` | Current user | - |
| `cd` | Change dir | `path` |
| `mkdir` | Create dir | `path` |
| `rm` | Remove | `path` |
| `cp` | Copy | `source, dest` |
| `mv` | Move | `source, dest` |
| `grep` | Search | `pattern, path` |
| `kill` | Kill process | `pid` |
| `write` | Write file | `content, path` |
| `run` | Execute | `command, ...args` |

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

The shell connects to the Python AI engine via:

**Unix Socket** (preferred for production):
```rust
let stream = std::os::unix::net::UnixStream::connect("/var/run/bantu-ai.sock");
```

**Stdio** (for subprocess mode):
```rust
let mut child = Command::new("python")
    .args(["-m", "bantu_ai.engine"])
    .stdout(Stdio::piped())
    .stdin(Stdio::piped())
    .spawn()?;
```

**Message format** (JSON):
```json
{
  "type": "tool_call",
  "tool": "ls",
  "args": ["/home"],
  "context": {}
}
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
