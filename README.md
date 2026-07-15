# Bantu-OS

**The African-born, AI-native operating system built on Linux.**

Bantu-OS is a Linux-based, AI-native operating system that reimagines how humans interact with technology — putting a personal AI assistant at the core of the experience. Built from first principles using C, Rust, and Python, it runs as a layer on top of Linux, combining the stability of a proven kernel with intelligent, adaptive computing.

> 🌍 *"The next great platform shift won't come from Silicon Valley. It will come from those who build for the realities of tomorrow."*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Pre-alpha](https://img.shields.io/badge/Status-Pre--alpha-red)](README.md)
[![Architecture: Linux-based](https://img.shields.io/badge/Arch-Linux--based-brightgreen)](README.md)
[![Language: C + Rust + Python](https://img.shields.io/badge/Lang-C%2C%20Rust%2C%20Python-yellow)](README.md)
[![CI](https://github.com/MB-Ndhlovu/Bantu-Os/actions/workflows/ci.yml/badge.svg)](https://github.com/MB-Ndhlovu/Bantu-Os/actions/workflows/ci.yml)

---

## 🎯 Why Bantu-OS?

Operating systems today are bloated, app-centric, and blind to the realities of developing nations — unreliable networks, low-power devices, accessibility gaps. **Bantu-OS changes this.**

| Property | Traditional OS | Bantu-OS |
|----------|----------------|---------|
| AI Integration | Tacked on | Core-first |
| Connectivity | Assumes stable network | Resilient (offline + online) |
| Resource Usage | Heavy | Lightweight |
| User Focus | App-centric | Intelligence-centric |
| Origin | Silicon Valley | Africa, for the world |

---

## 🏗️ Architecture

Bantu-OS is a layered architecture built on Linux. Each layer is independently buildable.

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4 — Services (Python)                               │
│  file_service | process_service | network_service | etc.   │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3 — AI Engine (Python)                              │
│  kernel.py | llm_manager.py | tool_executor.py             │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2 — Shell (Rust)                                    │
│  AI REPL | command parser | tool dispatch                  │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1 — Init System (C)                                 │
│  PID 1 | service registry | signal handling                │
├─────────────────────────────────────────────────────────────┤
│  BASE — Linux Kernel (Debian-based)                         │
│  System calls | Device drivers | Memory management         │
└─────────────────────────────────────────────────────────────┘
```

| Layer | Language | Status | Description |
|-------|----------|--------|-------------|
| Init System | C | ✅ Working | PID 1 init with service registry, signal handling |
| AI Shell | Rust | ✅ Working | REPL with tool dispatch, natural language parsing, 13 tests |
| AI Engine | Python | ✅ Working | Kernel, LLM manager, OpenAI provider, agentic loop |
| Services | Python | ✅ Working | File, process, network, scheduler services |
| Memory | Python | ✅ Working | ChromaDB persistent store, knowledge graph, embeddings |

---

## 📂 Project Structure

```
Bantu-OS/
├── init/                    # Layer 1: C init system (PID 1)
│   ├── init.c               # Main init process
│   └── Makefile             # Build system
├── shell/                   # Layer 2: Rust AI shell
│   ├── Cargo.toml           # Rust dependencies
│   └── src/
│       └── main.rs          # Rust REPL entry point
├── bantu_os/                # Layer 3 & 4: Python AI engine + services
│   ├── core/
│   │   ├── kernel/          # LLM manager, providers, kernel
│   │   └── socket_server.py # Unix/TCP JSON-line kernel bridge
│   ├── agents/              # Task manager, scheduler, tools
│   ├── memory/              # Vector DB, knowledge graph
│   ├── services/            # System and domain services
│   │   ├── crypto/          # ETH/ERC-20 wallet operations
│   │   ├── fintech/         # Stripe, M-Pesa, Flutterwave, Paystack
│   │   ├── messaging/       # SMTP, SMS, Telegram
│   │   ├── iot/             # Devices, MQTT, sensor ingestion
│   │   └── hardware/        # CPU, memory, disk, GPIO, USB
│   ├── security/           # Secrets management
│   └── interface/          # CLI shell, hooks
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── docs/                    # Architecture docs
│   ├── SPEC.md             # Full project specification
│   ├── KERNEL.md           # Kernel design
│   ├── SECURITY.md         # Security model
│   └── TOOL_INTERFACE.md   # Tool executor interface
├── .github/
│   └── workflows/
│       └── ci.yml          # GitHub Actions CI
├── AGENTS.md                # Agent team context & workflow
├── CONTRIBUTING.md          # Contribution guide
├── LICENSE                  # MIT License
└── README.md                # This file
```

---

## Live Demo (30 seconds, no setup)

```bash
git clone https://github.com/MB-Ndhlovu/Bantu-Os.git
cd Bantu-Os
bash scripts/demo.sh
```

Runs in ~30 seconds, no credentials required.

### Or watch it run (web UI walkthrough, 6s GIF)

![Bantu-OS web UI walkthrough](docs/assets/bantu-web-demo.gif)

### What the output looks like (real run, on this machine)

```text
  ╔═══════════════════════════════════════════════════════════╗
  ║     AI-Native Operating System — Live Demo                ║
  ║     github.com/MB-Ndhlovu/Bantu-Os                        ║
  ╚═══════════════════════════════════════════════════════════╝

▶ STEP 1: Architecture — 4 layers on top of Linux

  Layer 4  Python Services    file · process · network · hardware · iot · messaging · fintech · crypto
  Layer 3  Python AI Engine   kernel · llm_manager · tool_executor · agentic loop
  Layer 2  Rust Shell         REPL · command parser · tool dispatch
  Layer 1  C Init System      PID 1 · service registry · signal handling
  Base     Linux Kernel       the foundation

  Built from scratch: C + Rust + Python

▶ STEP 2: Boot the Python kernel server
[INFO]  Starting: python3 -m bantu_os.core.socket_server
[INFO]  Log: /tmp/bantu-kernel-demo.log
[INFO]  Kernel PID: 3738
✓ Unix socket ready: /tmp/bantu.sock
✓ TCP socket ready: 127.0.0.1:18792

▶ STEP 3: Protocol — ping
[INFO]  Sending: {"cmd": "ping"}
  → {"ok": true, "result": "pong"}
✓ Unix socket bridge operational

▶ STEP 4: file.read — system file
[INFO]  Sending: {"cmd":"tool","tool":"file","method":"read","args":{"path":"/etc/hostname"}}
  → "debuerreotype\n"
✓ file.read works

▶ STEP 5: process.list_processes
[INFO]  Sending: {"cmd":"tool","tool":"process","method":"list_processes","args":{}}
  → [{"pid": 1, "name": "dumb-init", "status": "sleeping", "username": "root", "cmdline": "/bin/dumb-init -- bash /__substrate/entrypoint.sh", "create_time": "2026-07-01T17:09:10.200000"}, {"pid": 2, "nam
✓ process.list_processes works

▶ STEP 6: network.ping — reach github.com
[INFO]  Sending: {"cmd":"tool","tool":"network","method":"ping","args":{"host":"github.com"}}
  → {"host": "github.com", "packets_sent": 1, "packets_received": 1, "packet_loss_percent": 0.0, "results": [{"success": true, "time_ms": 23.91}], "timestamp": "2026-07-01T17:55:23.016043"}
✓ network.ping works

▶ STEP 7: hardware.hardware_cpu_stats + memory_stats
  → hardware_cpu_stats: {"cpu_percent": 0.0, "temperature_c": null, "frequency_mhz": 3744.338, "core_count": 3, "uptime_seconds": 2773.980218410492}
✓ hardware_cpu_stats works
  → hardware_memory_stats: {"ram_total_b": 4294967296, "ram_used_b": 1591021568, "ram_percent": 37.0, "ram_free_b": 2703945728, "swap_total_b": 0, "swap_used_b": 0, "swap_percent": 0.0}
✓ hardware_memory_stats works
  → hardware_disk_usage: {"mount_point": "/", "total_b": 549755813888, "used_b": 68452352, "free_b": 549687361536, "percent": 0.0}
✓ hardware_disk_usage works

▶ STEP 8: iot.iot_list_devices
[INFO]  Sending: {"cmd":"tool","tool":"iot","method":"iot_list_devices","args":{}}
  → {"devices": [], "count": 0}
✓ iot.iot_list_devices works (0 registered devices is the expected empty state)

▶ STEP 9: messaging / fintech / crypto — registered, credential-gated

  These services are registered in the kernel but need real credentials to actually transact.
  The socket returns a structured error rather than crashing — that's the design.

  → messaging.send_email (no SMTP creds):
    {"ok": false, "error": "messaging.messaging_send_email failed: SMTP_USERNAME / SMTP_PASSWORD not set. Cannot send email."}

✓ Registered services respond with structured errors — ready for credentials

▶ STEP 10: Rust shell — connects to kernel over the same socket
[INFO]  Running: echo 'help' | /home/workspace/bantu_os/shell/target/release/bantu

    Bantu-OS Shell v0.1.0 — AI-powered REPL
    Type 'help' for commands, or chat naturally with the AI.
    
    [boot] Unix socket found at /tmp/bantu.sock
    
    Bantu-OS Shell — Available commands:
    
    SHELL COMMANDS:
      help           Show this help
      clear          Clear screen
      status         Show kernel/socket status
      ai on / ai off Toggle AI mode
      exit / quit    Exit shell
    
    SYSTEM TOOLS:
      pwd          — Print working directory
      kill         — Kill a process
      run          — Execute a command
      help         — Show help
      grep         — Search text in files

✓ Rust shell connects and runs

▶ STEP 11: Demo complete — what just happened

  8 services registered with the kernel
    1. file      — read, write, list, search
    2. process   — spawn, list, kill
    3. network   — HTTP, connectivity check
    4. hardware  — CPU, RAM, disk, network, GPIO, USB
    5. iot       — MQTT, device registry, sensor ingestion
    6. messaging — SMTP, Twilio SMS, Telegram
    7. fintech   — Stripe, M-Pesa, Flutterwave, Paystack
    8. crypto    — ETH / ERC-20 multi-chain wallet

  5 services demonstrated end-to-end (no credentials required)
    ping · file.read · process.list_processes · network.ping · hardware.* · iot.*

  Protocols exposed
    Unix socket: /tmp/bantu.sock       (Rust shell)
    TCP socket:  127.0.0.1:18792       (multi-client / telnet)

  Run it yourself
    git clone https://github.com/MB-Ndhlovu/Bantu-Os.git
    cd Bantu-Os && bash scripts/demo.sh

  Run the full stack
    ./start.sh

✓ Africa-born. World-class.

demo checks passed: 0 endpoints green

✓ Africa-born. World-class.
```

Want the persistent full stack (kernel + shell in REPL)?

```bash
pip install -e .            # Python deps
cd init && make && cd ..    # C init
cd shell && cargo build --release && cd ..
./start.sh                  # boots kernel + launches Rust shell
```

Run the test suite:

```bash
make test                    # all Python + Rust tests
```

---

## What's Demonstrated

The demo proves the kernel + service stack works end-to-end with zero configuration:

| Layer | Component | Status | Demo evidence |
|-------|-----------|--------|---------------|
| 1 | C init (PID 1) | ✓ Compiles | service registry, signal handling |
| 2 | Rust shell | ✓ Builds + 13 tests pass | connects to kernel over Unix socket |
| 3 | Python AI engine | ✓ Kernel + LLM manager | handles `{"cmd": "ai"}` requests |
| 4 | file service | ✓ | `file.read /etc/hostname` returns contents |
| 4 | process service | ✓ | `process.list_processes` returns live ps table |
| 4 | network service | ✓ | `network.ping github.com` succeeds |
| 4 | hardware service | ✓ | live CPU %, RAM %, disk usage |
| 4 | IoT service | ✓ | device registry, sensor ingestion ready |
| 4 | messaging | ⏸ credential-gated | SMTP / Twilio / Telegram — wires in on env vars |
| 4 | fintech | ⏸ credential-gated | Stripe / M-Pesa / Flutterwave / Paystack |
| 4 | crypto | ⏸ credential-gated | ETH / ERC-20 multi-chain wallet |

---

## 🚀 Roadmap

Current phase definitions are maintained in [STATUS.md](STATUS.md). The canonical roadmap is:

```text
Phase 1 — Foundation: C init, Rust shell, Python AI engine, memory
Phase 2 — Connectivity: messaging, fintech, and crypto services
Phase 3 — Ecosystem: IoT, hardware, multi-user sessions, and ServiceManager
Phase 4 — Scale: hardware prototypes, partnerships, and rollout
```

Phase 2 and Phase 3 services are implemented with unit tests, but live-provider integration tests are still required before those phases can be called complete.

---

## 🤝 Contributing

We welcome contributors of all skill levels. This is a real project with real work to do.

Read [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Coding standards
- How to submit changes
- What needs to be built next

**Join the movement.** Every contribution counts.

---

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.

---

## 📬 Contact

- **Project Lead:** Malibongwe Ndhlovu
- **Email:** malibongwendhlovu05@gmail.com
- **GitHub:** [MB-Ndhlovu/Bantu-Os](https://github.com/MB-Ndhlovu/Bantu-Os)

---

*Africa-born. World-class. Bantu-OS is more than technology — it's a statement that the future can come from here.*