# Bantu-OS Specification

**Version:** 0.1.0  
**Status:** Pre-alpha  
**Architecture:** Linux-based, AI-native personal operating system

---

## 1. Project Overview

Bantu-OS is an African-born, AI-native operating system built on Linux. It reimagines the OS by making AI the primary interface — not an app running on top of an OS, but an OS where AI is the orchestrating intelligence that mediates between the user and all system resources.

The goal is a lightweight, fast, security-conscious OS that works across modern and low-power hardware, bridges the digital divide with resilient connectivity, and brings African-led innovation to the global OS landscape.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│                    USER LAYER                        │
│         (Natural language, voice, CLI)              │
├─────────────────────────────────────────────────────┤
│                  LAYER 4 — AI SERVICES               │
│         (Python: LLM engine, agents, memory,         │
│          file service, process service, network)     │
├─────────────────────────────────────────────────────┤
│                  LAYER 3 — AI SHELL                  │
│              (Rust: REPL, tool dispatch)             │
├─────────────────────────────────────────────────────┤
│                  LAYER 2 — INIT SYSTEM               │
│              (C: PID 1, service registry)            │
├─────────────────────────────────────────────────────┤
│                  LAYER 1 — LINUX KERNEL              │
│            (Standard Linux, no modifications)        │
└─────────────────────────────────────────────────────┘
```

---

## 3. Layer Descriptions

### Layer 0 — Linux Kernel
- Standard Linux kernel (no modifications)
- Provides: process management, memory, file system, networking, hardware abstraction
- Bantu-OS does NOT write its own kernel — it runs ON Linux

### Layer 1 — C Init System (bantu_os/init/)
- **PID 1** — replaces systemd/OpenRC as the first user-space process
- Service registry: register services, start/stop/restart
- Dependency resolution between services
- Minimal footprint — no systemd complexity
- **Language:** C (gcc)

### Layer 2 — Rust AI Shell (bantu_os/shell/)
- Command REPL running in userspace
- Parses natural language commands
- Dispatches tool calls to Layer 3 Python engine via IPC (Unix socket or stdin/stdout)
- Manages session state and context
- **Language:** Rust (cargo)

### Layer 3 — Python AI Engine (bantu_os/bantu_os/)
- LLM Manager — pluggable providers (OpenAI, Anthropic, local LLaMA)
- Kernel — orchestrates prompts, tools, and memory
- Agent Loop — task execution, tool use, result handling
- Memory — vector DB + knowledge graph for persistent context
- **Language:** Python 3.9+

### Layer 4 — Python System Services (bantu_os/bantu_os/services/)
- **FileService** — read, write, list, search files via AI tool calls
- **ProcessService** — spawn, monitor, kill processes
- **SchedulingService** — calendar, reminders, cron-like scheduling
- **NetworkService** — HTTP requests, API calls, connectivity checks
- Each service exposes tools via a JSON schema

---

## 4. Language Breakdown

| Layer | Language | Purpose |
|-------|----------|---------|
| Kernel | C | Init system, PID 1, service manager |
| AI Shell | Rust | REPL, command parsing, tool dispatch |
| AI Engine | Python | LLM, agents, memory, system services |
| Build/CI | Shell + YAML | Makefiles, GitHub Actions |
| Docs | Markdown | All documentation |

---

## 5. Phase 1 Features (MVP)

### Must Have
- [x] C init system that boots and manages at least 3 services
- [x] Rust shell REPL that accepts text commands
- [x] Python AI engine with working LLM integration (OpenAI)
- [x] Tool executor that dispatches commands to Python services
- [x] File service (read, write, list files)
- [x] Memory module (vector store + knowledge graph)
- [x] Working CI pipeline (pytest + cargo check + gcc check)
- [x] SPEC.md, CONTRIBUTING.md, SECURITY.md

### Should Have
- [x] Process service (spawn and manage processes)
- [x] Scheduling service (calendar integration)
- [x] Network service (HTTP client)
- [ ] Docker build environment
- [x] Basic integration tests

### Could Have
- [ ] Voice interface (text-to-speech, speech-to-text)
- [ ] Anthropic/Grok provider support
- [ ] Local LLaMA integration
- [ ] IoT service (MQTT)

---

## 6. Directory Structure

```
bantu_os/
├── AGENTS.md              # Agent team instructions
├── Makefile               # Build orchestration
├── Dockerfile             # Build environment
├── README.md              # Project overview
├── SPEC.md                # This file
├── .github/
│   └── workflows/
│       └── ci.yml         # GitHub Actions CI
├── scripts/
│   └── dev-setup.sh       # One-script dev environment
├── init/                  # Layer 1: C init system
│   ├── init.c             # PID 1, service registry
│   └── Makefile
├── shell/                 # Layer 2: Rust AI shell
│   ├── Cargo.toml
│   ├── src/
│   │   └── main.rs        # REPL + tool dispatch
│   └── Makefile
├── bantu_os/              # Layer 3 & 4: Python AI engine
│   ├── __init__.py
│   ├── core/
│   │   ├── kernel/
│   │   │   ├── llm_manager.py
│   │   │   ├── kernel.py
│   │   │   └── providers/
│   │   │       ├── base.py
│   │   │       └── openai_chat.py
│   │   └── utils/
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── task_manager.py
│   │   ├── scheduling_agent.py
│   │   └── tool_executor.py
│   ├── services/
│   │   ├── file_service.py
│   │   ├── process_service.py
│   │   ├── scheduling_service.py
│   │   └── network_service.py
│   ├── memory/
│   │   ├── vector_db.py
│   │   └── knowledge_graph.py
│   ├── security/
│   │   └── basic_secrets.py
│   └── interface/
│       ├── cli/
│       └── hooks/
├── docs/
│   ├── SPEC.md
│   ├── SECURITY.md
│   ├── KERNEL.md
│   ├── TOOL_INTERFACE.md
│   └── CONTRIBUTING.md
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
└── initramfs/
    └── build.sh
```

---

## 7. Contributing

See `docs/CONTRIBUTING.md` for full guide.

**Key rules:**
- All code must compile and pass tests before commit
- Python: run `make format` before committing
- Rust: run `cargo fmt` before committing
- C: run `make clean && make` before committing
- No hardcoded API keys or secrets — use environment variables

---

## 8. Roadmap

### Phase 1 — Foundation (current)
Linux-based OS with working AI shell, Python AI engine, and basic services.

### Phase 2 — Connectivity
Messaging integration, fintech APIs (Stripe, African payment providers), crypto wallet basics.

### Phase 3 — Ecosystem
IoT device support, hardware prototypes, mobile companion app.

### Phase 4 — Scale
Enterprise partnerships, licensing, global rollout.

---

## 9. Contact

- GitHub Issues: https://github.com/MB-Ndhlovu/Bantu-Os/issues
- Email: malibongwendhlovu05@gmail.com