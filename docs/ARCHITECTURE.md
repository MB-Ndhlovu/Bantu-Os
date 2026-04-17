# Bantu-OS Architecture

## Overview

Bantu-OS is a Linux-based AI-native operating system. It is structured in **5 abstraction layers**, each building on the one below it.

```
┌──────────────────────────────────────────────────────┐
│  LAYER 4 — Python AI Services   (bantu_os/)          │
│  LLMs, agents, memory, file/process/network services  │
├──────────────────────────────────────────────────────┤
│  LAYER 3 — Rust Shell            (shell/)            │
│  REPL, command parsing, tool dispatch                 │
├──────────────────────────────────────────────────────┤
│  LAYER 2 — C Init Daemon        (init/)              │
│  PID 1, service registry, signal handling, IPC        │
├──────────────────────────────────────────────────────┤
│  LAYER 1 — Linux Kernel          (kernel/)           │
│  Process scheduling, memory, device I/O, syscalls     │
├──────────────────────────────────────────────────────┤
│  LAYER 0 — Hardware             (bare metal or VM)    │
└──────────────────────────────────────────────────────┘
```

---

## Layer 0 — Hardware

Physical or virtual hardware: CPU, RAM, storage, network interfaces.

- **Bare metal**: x86_64 server or workstation
- **Virtual machine**: QEMU/KVM, VirtualBox, cloud hypervisors
- **Container** (dev only): Linux namespace isolation, shares host kernel

---

## Layer 1 — Linux Kernel

The kernel is the foundation. Bantu-OS targets **Linux 6.x** on **x86_64**.

**Responsibilities:**
- Process scheduling ( CFS scheduler)
- Memory management (virtual memory, cgroups)
- Device I/O (block, network, character devices)
- Filesystem operations (ext4, btrfs, tmpfs, procfs, sysfs)
- Networking (TCP/IP stack)
- System call interface (`read`, `write`, `pipe`, `epoll`, `clone`, `mount`, etc.)

**Kernel config**: See `kernel/config` — minimal, embedded/lightweight, no desktop bloat.

**Build**: `kernel/build.sh` compiles the kernel with the custom config.

**Boot flow:**
```
Bootloader (GRUB/QEMU) → loads kernel + initramfs
                          → kernel mounts initramfs as rootfs
                          → executes /init (C init binary in initramfs)
```

---

## Layer 2 — C Init Daemon

The C init (`init/init.c`) runs as **PID 1** inside the initramfs environment.

**Responsibilities:**
1. **Bootstraps** — mounts `/proc`, `/sys`, `/dev`, `/run`
2. **Creates IPC socket** — `/run/bantu/init.sock` for Python service registration
3. **Starts services** — forks and execs the Python AI engine
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

**Source**: `init/init.c`, `init/services.c`, `init/services.h`

---

## Layer 3 — Rust Shell

The Rust shell (`shell/src/main.rs`) is the interactive entry point for users.

**Responsibilities:**
- REPL loop (read-eval-print)
- Command parsing and tokenization
- Tool dispatch protocol — calls Python services via stdio or IPC
- Rust FFI bindings for any C init socket communication

**Source**: `shell/src/main.rs`, `shell/Cargo.toml`

---

## Layer 4 — Python AI Services

Python services are the user-facing layer of Bantu-OS.

**Core components:**
- `bantu_os/core/kernel/` — AI kernel, LLM manager
- `bantu_os/agents/` — agentic loop, task manager, tool executor
- `bantu_os/memory/` — vector DB (ChromaDB), knowledge graph, session management
- `bantu_os/services/` — file, process, network, scheduler services
- `main.py` — entry point, starts all services

**IPC with C init:**
- Python services connect to `/run/bantu/init.sock`
- Register service name + PID on startup
- Send periodic health heartbeats
- Receive `SIGTERM` via init on shutdown

**Rust bridge** (`bantu_os/c_bridge/`): Type-safe wrappers around the socket protocol.

---

## Boot Sequence (Full)

```
1. Bootloader loads: kernel (bzImage) + initramfs (initramfs.cpio.gz)
2. Kernel decompresses, initializes, mounts initramfs as rootfs
3. Kernel executes /init (C init binary) → PID 1
4. C init:
   a. Mount /proc, /sys, /dev, /run (tmpfs)
   b. Create /run/bantu/init.sock
   c. Parse /etc/bantu/services.conf (if present)
   d. fork() + exec(python3 main.py) → Python AI engine
5. Python services start, register via c_bridge → init.sock
6. C init enters epoll event loop:
   - Monitor SIGCHLD from children
   - Accept socket connections (service registration)
   - Handle control commands (shutdown, restart)
7. On shutdown (SIGTERM):
   a. C init sends SIGTERM to all services
   b. Waits for graceful exit (5s timeout)
   c. SIGKILL any remaining processes
   d. syncfs + reboot()
```

---

## Directory Map

```
bantu-os/
├── kernel/                 # Layer 1: Linux kernel
│   ├── config              # .config for x86_64 (minimal/embedded)
│   └── build.sh            # Kernel build script
├── boot/                   # Boot artifacts
│   ├── initramfs/          # Initramfs build system
│   │   ├── build.sh        # Builds initramfs.cpio.gz
│   │   └── overlay/        # Files packaged into initramfs
│   │       ├── init        # C init binary
│   │       ├── bin/        # Busybox symlinks
│   │       ├── lib/        # Shared libraries
│   │       └── run/bantu/  # Runtime socket directory
├── init/                   # Layer 2: C init system
│   ├── init.c              # PID 1 entry point
│   ├── services.c          # Service registry
│   ├── services.h          # Service definitions
│   ├── syscall.c           # System call wrappers
│   └── Makefile
├── shell/                  # Layer 3: Rust shell
│   ├── src/main.rs
│   └── Cargo.toml
├── bantu_os/               # Layer 4: Python AI services
│   ├── core/kernel/        # AI kernel, LLM manager
│   ├── agents/             # Agent loop, task manager
│   ├── memory/             # Vector DB, graph, embeddings
│   ├── services/           # File, process, network services
│   └── c_bridge/           # Rust-Python FFI bridge
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md      # This file (5-layer overview)
│   ├── KERNEL.md           # Layer 1 details
│   ├── INIT.md             # Layer 2 details
│   └── INDEX.md            # Documentation index
├── Makefile                # Root build orchestrator
└── README.md
```

---

## Build Targets

The root `Makefile` provides:

| Target | Description |
|--------|-------------|
| `make kernel` | Build the Linux kernel using `kernel/config` |
| `make initramfs` | Build the initramfs via `boot/initramfs/build.sh` |
| `make image` | Assemble final OS image (kernel + initramfs + rootfs) |
| `make all` | Build kernel + initramfs |
| `make clean-kernel` | Remove kernel build artifacts |

---

## Design Principles

1. **Kernel is the source of truth** — all process lifecycle flows through it
2. **C init is minimal** — no business logic, only orchestration + IPC
3. **Rust for safety + performance** — shell and FFI bridge
4. **Python for expressiveness** — agents, LLMs, memory, rich ecosystem
5. **Graceful shutdown** — `SIGTERM` propagates cleanly PID 1 → services
6. **No runtime dependencies above the kernel** — each layer is self-contained

---

## Next Steps (Roadmap)

- [ ] Integrate `kernel/config` with CI to verify kernel builds
- [ ] Add rootfs creation to `make image` (stage3/rootfs.tar.gz)
- [ ] Add GRUB/QEMU config examples in `docs/`
- [ ] Benchmark kernel boot time and init sequence
- [ ] Add seccomp policy for C init (syscall filtering)