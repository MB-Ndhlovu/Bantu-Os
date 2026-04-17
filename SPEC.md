# Bantu-OS Specification

**Version:** 0.1.0
**Last Updated:** 2026-04-17
**Status:** Phase 1 — MVP

---

## Overview

Bantu-OS is a Linux-based AI-native operating system. It is designed from the ground up to have an AI agent as a first-class citizen — not bolted on top, but woven into the boot process, shell, and service layer.

The OS is built in discrete, composable layers. Each layer has a clearly defined responsibility and interface. The AI engine is the operating system.

**Bantu** ( Zulu/Xhosa: *person*) — because the OS treats the user as a person, not a root.

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Layer 4: Services (Python)             │
│  FileService, ProcessService,           │
│  NetworkService, Memory                  │
├─────────────────────────────────────────┤
│  Layer 3: AI Engine (Python)            │
│  Kernel, LLM Manager, Tool Executor,    │
│  Agentic Loop                           │
├─────────────────────────────────────────┤
│  Layer 2: Shell (Rust)                  │
│  REPL, Command Parser, Tool Dispatch    │
├─────────────────────────────────────────┤
│  Layer 1: Init (C)                     │
│  PID 1, Service Registry, Signal Handle │
├─────────────────────────────────────────┤
│  Base: Linux Kernel                     │
└─────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Language | Role |
|-------|----------|------|
| Base | — | Linux kernel, hardware abstraction |
| Layer 1 | C | Boot, PID 1, init, service registry, signal handling |
| Layer 2 | Rust | Interactive shell, REPL, command parsing, AI handoff |
| Layer 3 | Python | AI engine: kernel, LLM management, tool execution, agentic loop |
| Layer 4 | Python | System services: file ops, process mgmt, networking, persistent memory |

### Why Each Language

- **C:** Init must be PID 1 — only C or asm can occupy that role. C is lean, predictable, and compiles to minimal binaries.
- **Rust:** Shell is the primary user-facing interface. Rust provides memory safety without a garbage collector, fast execution, and excellent async I/O for the REPL and tool dispatch.
- **Python:** The AI engine is the most rapidly evolving component. Python's ecosystem (numpy, chromadb, openai, anthropic SDKs) makes it the natural choice for LLM integration and data processing.

---

## Directory Structure

```
bantu_os/
├── init/                    # Layer 1: C init system
│   ├── init.c              # PID 1, service registry, signal handling
│   └── Makefile
├── shell/                   # Layer 2: Rust shell
│   ├── src/main.rs         # REPL, command parser, AI dispatch
│   ├── src/commands/       # Built-in shell commands
│   ├── src/ai/             # AI handoff logic (socket + subprocess)
│   ├── Cargo.toml
│   └── tests/
├── bantu_os/               # Layer 3 & 4: Python AI engine + services
│   ├── core/
│   │   ├── kernel/         # Kernel: agentic loop, input processing
│   │   ├── llm/            # LLM manager: model routing, token tracking
│   │   ├── tool_executor/  # Tool schema registry, execution
│   │   ├── memory/         # ChromaDB vector store, session history
│   │   └── socket_server.py # Unix socket bridge (Rust ↔ Python)
│   ├── services/
│   │   ├── file_service.py
│   │   ├── process_service.py
│   │   └── network_service.py
│   └── tests/
├── docs/                   # Architecture & design docs
├── kernel/                 # Linux kernel config (future)
├── boot/                   # initramfs structure (future)
└── Makefile               # Root build target
```

---

## Components

### Layer 1 — C Init (`init/`)

**Responsibility:** Be PID 1. Start the Rust shell as PID 2. Maintain the service registry. Handle SIGTERM/SIGINT gracefully.

**Current State:** ✅ Working. `init.c` compiles and runs as PID 1 in a container.

**Key interfaces:**
- `void init_start_service(const char* name)` — start a service by name
- `void init_register_service(const char* name, pid_t pid)` — register a running process
- Signal handlers for SIGTERM (graceful shutdown), SIGCHLD (reap zombies)

### Layer 2 — Rust Shell (`shell/`)

**Responsibility:** Present an interactive REPL to the user. Parse commands. Dispatch built-in commands directly. Forward AI-mode commands to the Python kernel via Unix socket.

**Current State:** ✅ Builds, 13 tests passing. REPL, built-in commands, and socket client all working.

**Key modules:**
- `main.rs` — entry point, REPL loop, command routing
- `commands/` — built-in shell commands (ls, cd, ps, kill, etc.)
- `ai.rs` — AI mode: `handle_ai_input()` calls the socket client

**AI Handoff Protocol:**
```json
// Shell → Kernel
{"cmd": "ai", "text": "<user input>"}

// Kernel → Shell (success)
{"ok": true, "result": "<AI response text>"}

// Kernel → Shell (error)
{"ok": false, "error": "<error message>"}
```

### Layer 3 — Python AI Engine (`bantu_os/core/`)

**Responsibility:** Process user input through an agentic loop. Maintain conversation context. Execute tools. Manage LLM calls.

**Current State:** ✅ Kernel, LLM manager, tool executor, agentic loop — 43+ tests passing.

**Key modules:**
- `kernel/kernel.py` — `agentic_loop(user_input)` — main entry point
- `kernel/process_input.py` — input parsing and routing
- `llm/manager.py` — `LLMManager` — handles model routing, token budgets
- `llm/providers/` — OpenAI, Anthropic, Ollama provider implementations
- `tool_executor/schema.py` — JSON schema for all available tools
- `tool_executor/executor.py` — `execute_tool(name, params)` — runs a tool and returns result

### Layer 4 — Services (`bantu_os/services/`)

**Responsibility:** Provide secure, structured access to system operations. The AI never runs arbitrary code — it calls services.

**Current State:** ✅ FileService, ProcessService, NetworkService — all tested.

**Tool Schema (via `schema.py`):**
```json
{
  "name": "file_read",
  "description": "Read contents of a file",
  "parameters": {
    "path": {"type": "string", "description": "Absolute path to file"}
  }
}
```

### Memory (`bantu_os/core/memory/`)

**Responsibility:** Give the AI persistent context across sessions. Semantic search over conversation history. Knowledge graph for long-term facts.

**Current State:** ✅ ChromaDB vector store (9 tests), session manager.

---

## Roadmap

### Phase 1: MVP (Current)
**Goal:** Demonstrate the core loop — user types → shell → kernel → AI response.

- [x] C init as PID 1
- [x] Rust shell with REPL and built-in commands
- [x] Python kernel with LLM manager and tool executor
- [x] ChromaDB memory
- [x] Python services (file, process, network)
- [x] Unix socket bridge (Rust ↔ Python) ← **CURRENT TASK**
- [ ] C init wiring into service registry
- [ ] End-to-end smoke test (boot → REPL → AI → response)

### Phase 2: System Services
**Goal:** Make Bantu-OS usable as a development environment.

- Service manager daemon (replaces manual service starts)
- Persistent agentic context across shell sessions
- User identity and session management
- Filesystem sandboxing per session

### Phase 3: Ecosystem
**Goal:** Make Bantu-OS a platform.

- Package manager for AI tools/agents
- Multi-user support (multiple AI agents per system)
- Network API for remote agent access
- Bootable disk image (ISO/USB)

---

## Contribution Guidelines

### Commit Convention

```
<type>(<scope>): <description>
```

**Types:** `feat` | `fix` | `docs` | `test` | `refactor` | `chore`

**Examples:**
- `feat(socket): bridge Rust shell to Python kernel via Unix socket`
- `fix(llm): handle rate limit errors in OpenAI provider`
- `docs(readme): add architecture diagram`
- `test(kernel): add regression test for empty input handling`

### Branch Strategy

```
main           — stable, shippable
feat/*         — feature branches (from main)
fix/*          — bug fix branches (from main)
```

**Workflow:**
1. `git fetch upstream`
2. `git checkout main && git pull upstream main`
3. `git checkout -b feat/your-feature-name`
4. Make changes, write tests
5. `python -m pytest tests/ -v` — ALL must pass
6. `cargo test` — Rust tests must pass (if applicable)
7. `git add . && git commit -m "feat(scope): description"`
8. `git push origin feat/your-feature-name`
9. Open a PR on GitHub

### Code Standards

**Python:** PEP 8, typed (use `from __future__ import annotations`), docstrings on all public classes/functions.

**Rust:** `cargo fmt` before commit, `clippy` warnings must be resolved, docs on all public items.

**C:** Comments in C style (`/* ... */`), descriptive variable names, no magic numbers — use constants.

### Testing Policy

- Every new module needs unit tests
- Every bug fix needs a regression test
- All tests must pass in CI before merging to main
- Minimum test coverage target: 80% for Python core modules

---

## Getting Started

```bash
# Clone the repo
git clone https://github.com/MB-Ndhlovu/Bantu-Os.git
cd Bantu-Os

# Build Rust shell
cd shell && cargo build && cd ..

# Install Python deps
pip install -r requirements.txt

# Run Python tests
python -m pytest bantu_os/tests/ -v

# Run Rust tests
cd shell && cargo test && cd ..

# Smoke test (two terminals)
# Terminal 1: start socket server
python -c "from bantu_os.core.socket_server import SocketServer; import asyncio; s = SocketServer('/tmp/bantu.sock'); asyncio.run(s.run())"

# Terminal 2: send test command
echo '{"cmd": "ai", "text": "hello"}' | socat - UNIX-CONNECT:/tmp/bantu.sock
```

---

## Open Questions / TBD

- [ ] Tool access control: should the AI ask for confirmation before destructive operations (`rm -rf`, `kill -9`)?
- [ ] Token budgeting: how do we cap spend per session?
- [ ] Multi-user: how do multiple users share one OS with separate AI contexts?
- [ ] Persistence: where does the AI store its memory by default — local disk or a remote vector store?
- [ ] Network API: should external clients be able to query the AI engine? What auth model?
