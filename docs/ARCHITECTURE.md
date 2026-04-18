# Bantu-OS Architecture

## Overview

Bantu-OS is a Linux-based AI-native operating system. It is structured in **4 abstraction layers**, each building on the one below it. Unlike a traditional OS, AI is the primary interface — not an app running on top.

```
┌──────────────────────────────────────────────────────┐
│  LAYER 4 — Python AI Services   (bantu_os/)          │
│  LLMs, agents, memory, file/process/network services  │
├──────────────────────────────────────────────────────┤
│  LAYER 3 — Python AI Engine    (bantu_os/core/)      │
│  Kernel, LLM manager, tool executor, agentic loop    │
├──────────────────────────────────────────────────────┤
│  LAYER 2 — Rust Shell          (shell/)              │
│  REPL, command parsing, AI handoff via Unix socket  │
├──────────────────────────────────────────────────────┤
│  LAYER 1 — C Init System       (init/)              │
│  PID 1, service registry, signal handling            │
├──────────────────────────────────────────────────────┤
│  BASE — Linux Kernel          (host kernel)          │
│  Process scheduling, memory, device I/O, syscalls  │
└──────────────────────────────────────────────────────┘
```

> **Note:** Bantu-OS runs as a process layer on the host Linux kernel. It does not compile a custom kernel or build an initramfs. The C init is for future embedded/targeted boot scenarios; the primary development and runtime flow runs the Python kernel and Rust shell as regular processes.

---

## Layer 0 — Hardware

Physical or virtual hardware: CPU, RAM, storage, network interfaces.

- **Bare metal**: x86_64 server or workstation
- **Virtual machine**: QEMU/KVM, VirtualBox, cloud hypervisors
- **Container** (development): Linux namespace isolation, shares host kernel

---

## Layer 1 — Linux Kernel

The kernel is the foundation. Bantu-OS runs on the **host kernel** — it does not compile its own.

**Responsibilities:**
- Process scheduling (CFS scheduler)
- Memory management (virtual memory, cgroups)
- Device I/O (block, network, character devices)
- Filesystem operations (ext4, btrfs, tmpfs, procfs, sysfs)
- Networking (TCP/IP stack)
- System call interface (`read`, `write`, `pipe`, `epoll`, `clone`, `mount`, etc.)

**Bantu-OS does not modify the kernel.** It uses the host kernel as-is.

---

## Layer 2 — C Init System (`init/`)

The C init (`init/init.c`) is the first user-space process (**PID 1**) in a full boot scenario.

**Responsibilities:**
1. **Bootstraps** — mounts `/proc`, `/sys`, `/dev`
2. **Creates IPC socket** — `/tmp/bantu.sock` (dev) or `/run/bantu/init.sock` (production)
3. **Starts services** — forks and execs the Rust shell and Python runtime
4. **Manages lifecycle** — reaps zombies via `SIGCHLD`, handles `SIGTERM` shutdown
5. **Event loop** — uses `epoll_create` to monitor child process file descriptors

**Key kernel interactions:**

| Kernel API | Usage |
|---|---|
| `clone(2)` / `fork(2)` | Spawn child processes |
| `pipe(2)` | Async log collection from services |
| `epoll_create(2)` | Event loop monitoring |
| `signalfd(2)` | Handle `SIGCHLD`, `SIGTERM` without polling |
| `mount(2)` | Set up `/proc`, `/sys`, cgroups |
| `unshare(2)` | Isolate services in namespaces |

**Source**: `init/init.c`, `init/services.c`

---

## Layer 3 — Rust Shell (`shell/`)

The Rust shell (`shell/src/main.rs`) is the interactive entry point for users.

**Responsibilities:**
- REPL loop with line editing
- Command parsing and tokenization
- Built-in shell commands (`ls`, `cd`, `ps`, `kill`, etc.)
- AI handoff — connects to Python kernel via Unix socket (`/tmp/bantu.sock`)
- Tool dispatch for non-AI commands

**Source**: `shell/src/main.rs`, `shell/src/parser.rs`, `shell/src/tools.rs`

**IPC with Python kernel:**
```rust
// Connect to the Python kernel Unix socket
let mut sock = std::os::unix::net::UnixStream::connect("/tmp/bantu.sock");
// Send AI command
sock.write_all(b"{\"cmd\": \"ai\", \"text\": \"hello\"}\n");
// Read response
let mut response = String::new();
sock.read_to_string(&mut response);
```

**Socket protocol** (JSON, one line per message):
```json
// Shell → Kernel (AI mode)
{"cmd": "ai", "text": "hello"}

// Kernel → Shell (success)
{"ok": true, "result": "Hello!"}

// Kernel → Shell (error)
{"ok": false, "error": "no API key"}
```

---

## Layer 4 — Python AI Engine (`bantu_os/`)

Python is the user-facing layer of Bantu-OS. It contains the AI engine and all system services.

**Core components:**

| Module | File | Purpose |
|--------|------|---------|
| Kernel | `bantu_os/core/kernel/kernel.py` | AI kernel, agentic loop, prompt routing |
| LLM Manager | `bantu_os/core/llm_manager.py` | Model routing, token budgets, provider abstraction |
| Tool Executor | `bantu_os/core/tool_executor/` | JSON schema registry, async tool execution |
| Socket Server | `bantu_os/core/socket_server.py` | Dual Unix socket + TCP bridge (Rust ↔ Python) |
| AI Engine | `bantu_os/ai/engine.py` | AIEngine class with built-in handlers |
| Agent Manager | `bantu_os/agents/agent_manager.py` | Multi-agent orchestration, tool registry, message passing |
| File Service | `bantu_os/services/file_service.py` | Read, write, list, search files |
| Process Service | `bantu_os/services/process_service.py` | Spawn, monitor, kill processes |
| Network Service | `bantu_os/services/network_service.py` | HTTP requests, API calls, connectivity |
| Memory | `bantu_os/core/memory/` | ChromaDB vector store, session management |

**Entry point**: `main.py` — starts the kernel server and registers all services.

---

## Boot Sequence

### Development (primary)
```bash
# 1. Build the Rust shell
cd shell && cargo build --release

# 2. Start the Python kernel + Rust shell together
./start.sh
  # a. start.sh starts socket_server.py (Python kernel)
  # b. Waits for /tmp/bantu.sock to appear
  # c. Pings the server to verify health
  # d. Launches shell/target/release/bantu (Rust shell)
  # e. Rust shell connects to /tmp/bantu.sock on first AI command

# 3. User interacts with Rust REPL
#    "ai hello" → Rust shell sends {"cmd":"ai","text":"hello"} over socket
#               → Python kernel processes via LLM
#               → Response returns over socket → Rust shell prints
```

### Production / Embedded (future)
```bash
# 1. Bootloader loads kernel + initramfs
# 2. Kernel executes /init (C init binary) → PID 1
# 3. C init mounts /proc, /sys, /dev
# 4. C init creates /run/bantu/init.sock
# 5. C init forks Python kernel + Rust shell
# 6. Python services register via socket_server
# 7. C init enters epoll event loop
# 8. On SIGTERM: C init sends SIGTERM to all services → graceful shutdown
```

---

## Directory Map

```
bantu-os/
├── README.md              # Project overview
├── AGENTS.md              # Agent team instructions
├── CONTRIBUTING.md       # Contribution guide
├── SPEC.md                # Full project specification
│
├── init/                  # Layer 2: C init system
│   ├── init.c             # PID 1 entry point
│   ├── services.c          # Service registry
│   ├── ipc/ipc.c          # IPC helpers
│   ├── syscall.c          # System call wrappers
│   └── Makefile
│
├── shell/                 # Layer 3: Rust shell
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs        # REPL entry point
│       ├── parser.rs      # Command parser
│       ├── tools.rs       # Tool registry + built-in tools
│       └── lib.rs
│
├── bantu_os/              # Layer 4: Python AI engine + services
│   ├── __init__.py
│   ├── main.py            # Entry point
│   ├── config.py          # Settings management
│   ├── core/
│   │   ├── kernel/        # Kernel + LLM manager
│   │   ├── llm_manager.py # Model routing, token budgets
│   │   ├── socket_server.py # Unix socket + TCP bridge
│   │   ├── tool_executor/ # Tool schema registry + executor
│   │   └── memory/        # ChromaDB vector store
│   ├── ai/
│   │   └── engine.py      # AIEngine with built-in handlers
│   ├── agents/
│   │   └── agent_manager.py # Multi-agent orchestration
│   ├── services/
│   │   ├── file_service.py
│   │   ├── process_service.py
│   │   ├── network_service.py
│   │   └── scheduler_service.py
│   └── security/
│       └── basic_secrets.py
│
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── agent/            # Agent tests
│   ├── kernel/           # Socket server tests
│   ├── integration/      # Integration tests
│   ├── conftest.py       # Pytest fixtures (stub LLM provider)
│   └── test_e2e_shell_kernel.py # End-to-end boot test
│
├── docs/                  # Architecture docs
│   ├── ARCHITECTURE.md   # This file
│   ├── KERNEL.md         # Kernel design details
│   ├── SHELL.md          # Rust shell documentation
│   ├── SECURITY.md       # Security model
│   ├── SPEC.md           # Project specification
│   └── INIT.md           # C init documentation
│
├── start.sh               # Boot launcher (Python kernel + Rust shell)
├── Makefile               # Root build orchestrator
└── .github/
    └── workflows/
        └── ci.yml        # GitHub Actions CI
```

---

## Build Targets

The root `Makefile` provides:

| Target | Description |
|--------|-------------|
| `make build` | Build Python package |
| `make test` | Run pytest + cargo test |
| `make docker-build` | Build Docker image |
| `make docker-run` | Run inside container |

**Quick start:**
```bash
git clone https://github.com/MB-Ndhlovu/Bantu-Os.git
cd Bantu-Os
pip install -e .          # Install Python deps
cd init && make            # Build C init
cd ../shell && cargo build --release  # Build Rust shell
python -m pytest tests/ -v # Run tests
./start.sh                # Launch full system
```

---

## Design Principles

1. **Kernel is the foundation** — host Linux handles all hardware and process scheduling
2. **C init is minimal** — only orchestration + IPC for PID 1 scenarios
3. **Rust for safety + performance** — shell with memory safety, no GC
4. **Python for expressiveness** — agents, LLMs, memory, rich ecosystem
5. **Socket over FFI** — Rust ↔ Python communicate via Unix socket, not FFI
6. **Graceful shutdown** — `SIGTERM` propagates cleanly PID 1 → services
7. **Test everything** — CI runs pytest + cargo test on every push/PR

---

## Next Steps (Roadmap)

- [ ] C init wiring — connect service registry to C init PID 1
- [ ] End-to-end boot test — full boot from C init to AI response
- [ ] ChromaDB memory — persistence across sessions
- [ ] Phase 2: Messaging, fintech, crypto services
- [ ] IoT service (MQTT) for hardware prototypes
