# Bantu-OS Kernel Architecture

## Layer Overview

Bantu-OS is structured in abstraction layers, each building on the one below it.
```
Layer 4 — Python AI Services   (bantu_os/)
Layer 3 — Python AI Engine    (bantu_os/core/kernel/)
Layer 2 — Rust Shell          (shell/)
Layer 1 — C Init System        (init/)
Layer 0 — Linux Kernel        (host kernel / container runtime)
```

---

## Layer 0 → Layer 1: Hardware to Linux Kernel

The Linux kernel is the foundation. It manages:
- Process scheduling
- Memory management
- Device I/O
- Filesystem operations
- Networking stack

All higher layers depend on kernel syscalls (`read`, `write`, `pipe`, `socket`, `epoll`, etc.).

---

## Layer 1 → Layer 2: C Init System (`init/`)

The C init daemon (`init/main.c`) is the first userspace process (`PID 1`). It:

1. **Bootstraps** — mounts `/proc`, `/sys`, `/dev` via kernel API
2. **Starts services** — spawns long-running daemons (Python runtime, network manager, etc.)
3. **Manages lifecycle** — reaps zombies, handles signals, restarts crashed services
4. **Inter-process communication** — uses `pipe(2)` for log pipes, `socket(2)` for control API

### Key interactions with the kernel

| Kernel feature | C Init usage |
|---|---|
| `clone(2)` / `fork(2)` | Spawn child processes |
| `pipe(2)` | Async log collection from child services |
| `epoll_create(2)` | Event loop monitoring service fds |
| `signalfd(2)` | Handle SIGCHLD, SIGTERM without polling |
| `mount(2)` | Set up `/proc`, `/sys`, cgroups |
| `unshare(2)` | Isolate service processes in namespaces |

### C Init → Python IPC

The C init exposes a local Unix domain socket at `/run/bantu/init.sock`. Python services connect to this socket to:
- Register their service name and PID
- Report health status
- Receive shutdown signals

```
C Init (PID 1)
  ├── fork() + exec(python3)
  │     └── Python services connect to /run/bantu/init.sock
  ├── epoll loop monitors:
  │     ├── SIGCHLD from children
  │     ├── socket accepts (service registration)
  │     └── control commands (shutdown, restart)
  └── SIGTERM → graceful shutdown sequence
```

---

## Layer 2 → Layer 3: Rust Shell

The Rust shell (`shell/src/main.rs`) is the primary user-facing interface. It:
- Provides a line-buffered REPL with built-in commands (`ls`, `cd`, `ps`, `kill`, etc.)
- Forwards AI commands to the Python kernel via Unix socket (`/tmp/bantu.sock`)
- Supports TCP mode (`127.0.0.1:18792`) for future multi-client scenarios

**IPC with Python kernel:**
```rust
let stream = std::os::unix::net::UnixStream::connect("/tmp/bantu.sock");
// Send: {"cmd": "ai", "text": "hello"}
// Receive: {"ok": true, "result": "..."}
```

## Layer 3 → Layer 4: Python Services (`bantu_os/`)

Python services are the intelligence layer. They:

1. **Kernel** (`bantu_os/core/kernel/kernel.py`) — AI agentic loop, prompt routing, memory
2. **Socket Server** (`bantu_os/core/socket_server.py`) — dual Unix socket + TCP bridge
3. **Agent Manager** (`bantu_os/agents/agent_manager.py`) — multi-agent orchestration
4. **Services** — FileService, ProcessService, NetworkService registered as tools

### Kernel interaction from Python

Python talks to the kernel through stdlib and native extensions:

```python
import os, socket, mmap, resource

# Process creation (via exec, not fork — inherits runtime)
os.setpgid(pid, pgid)   # process group management

# Networking
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(("0.0.0.0", 8080))

# Memory limits (via cgroups resource control)
resource.setrlimit(resource.RLIMIT_NPROC, (512, 512))
```

### Linux capabilities used

| Capability | Purpose |
|---|---|
| `CAP_NET_BIND_SERVICE` | Bind to privileged ports (<1024) |
| `CAP_SYS_ADMIN` | Mount filesystems, cgroup management |
| `CAP_SYS_RESOURCE` | Raise resource limits |
| `CAP_KILL` | Send signals to process group |

---

## Boot Sequence

```
1. Bootloader loads kernel + initramfs
2. Kernel mounts initramfs, executes /init (C init)
3. C init sets up mounts, pipes, epoll
4. C init forks Python runtime
5. Python services (Kernel, Agents, Memory) start
6. Python services register via c_bridge → C init socket
7. C init enters event loop — monitors services + signals
8. On shutdown: C init sends SIGTERM, waits, then SIGKILL
```

---

## initramfs Build

The `initramfs/` directory contains tooling to build the initial ramdisk.

### Contents

```
initramfs/
├── build.sh              # Build script — creates cpio archive
├── overlay/
│   ├── init              # Replacement /init (C init binary)
│   ├── bin/              # Minimal binaries (busybox, etc.)
│   ├── lib/              # Minimal shared libs
│   └── run/
│       └── bantu/
│           └── init.sock # Socket created at runtime
└── README.md
```

### Build

```bash
cd initramfs && ./build.sh
# Output: initramfs.cpio.gz
```

The resulting `initramfs.cpio.gz` is passed to the Linux kernel via the bootloader (GRUB, QEMU, etc.).

---

## Key Design Principles

1. **Kernel is the source of truth** — all process lifecycle flows through it
2. **C init is minimal** — it does not implement business logic, only orchestration
3. **Python is expressive** — agents, memory, and LLM logic live here
4. **Rust bridges safely** — type-safe FFI without unsafe Python everywhere
5. **Graceful shutdown** — SIGTERM propagates cleanly from init → services