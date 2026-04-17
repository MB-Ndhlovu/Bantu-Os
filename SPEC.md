# Bantu-OS — Project Specification

> **Single source of truth.** Every architectural decision, design choice, and future plan lives here. All other docs derive from this document.

---

## 1. Overview

**Bantu-OS** is a Linux-based, AI-native operating system that puts a personal AI assistant at the core of the computing experience.

Built from first principles with C, Rust, and Python, it runs as a layer on top of the Linux kernel. It is not a distro — it is a new interaction model for computing, designed from the ground up for intelligence-first, resilient, resource-efficient operation.

### Design Principles

| Principle | Rationale |
|-----------|-----------|
| AI at the core | Intelligence is the primary interface, not an app overlay |
| Resilient connectivity | Offline-first thinking; graceful degradation |
| Resource efficient | Targets low-power and emerging-market hardware |
| Africa-born, world-class | Built for the realities of developing regions, open to all |

---

## 2. Architecture

Bantu-OS is a **5-layer stacked architecture** built on the Linux kernel. Each layer is independently buildable and testable.

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4 — Services                                        │
│  Python                                                     │
│  FileService | ProcessService | NetworkService |            │
│  SchedulerService | MessagingService | FintechService |     │
│  CryptoService                                             │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3 — AI Engine                                        │
│  Python                                                     │
│  kernel.py | llm_manager.py | tool_executor.py |             │
│  agent_manager.py | task_manager.py                         │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2 — Shell                                            │
│  Rust                                                       │
│  AI REPL | command parser | tool dispatcher                 │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1 — Init System                                      │
│  C                                                          │
│  PID 1 | service registry | signal handling                 │
├─────────────────────────────────────────────────────────────┤
│  BASE — Linux Kernel (Debian-based)                         │
│  System calls | device drivers | memory management          │
└─────────────────────────────────────────────────────────────┘
```

### Layer Descriptions

| Layer | Language | Status | Role |
|-------|----------|--------|------|
| Layer 1 — Init | C | ✅ Working | PID 1 init process, service registry, signal handling |
| Layer 2 — Shell | Rust | ✅ Working | AI REPL, command parsing, natural language dispatch, tool routing |
| Layer 3 — AI Engine | Python | ✅ Working | Kernel orchestration, LLM management, agentic loop, tool execution pipeline |
| Layer 4 — Services | Python | ✅ Working | File, process, network, scheduler, messaging, fintech, crypto services |

### Communication Protocol

- **Rust Shell ↔ Python Kernel**: Unix socket (`/tmp/bantu.sock`) + TCP fallback (`127.0.0.1:18792`)
- **Tool protocol**: `{"cmd": "tool", "tool": "<service>", "method": "<method>", "args": {...}}`
- **AI protocol**: `{"cmd": "ai", "text": "..."}`

---

## 3. Language Choices

| Language | Layer | Why |
|----------|-------|-----|
| **C** | Layer 1 — Init | PID 1 init must be as close to the metal as possible. C gives us direct kernel ABI access, minimal footprint, and true PID 1 capability without a runtime dependency. |
| **Rust** | Layer 2 — Shell | Memory safety without garbage collection is critical for a long-running interactive shell. Rust's type system and zero-cost abstractions make it ideal for a performance-sensitive, I/O-bound REPL. |
| **Python** | Layers 3 & 4 — AI Engine & Services | The AI ecosystem (LLM providers, vector stores, embeddings) is Python-native. Python's agility and rich library ecosystem make it the obvious choice for rapid AI engine development and service prototyping. |

---

## 4. Component Map

```
bantu_os/
├── init/                      # Layer 1: C init system
│   ├── init.c                 # PID 1 entry point, service registry, signals
│   └── Makefile              # Build: cd init && make
│
├── shell/                     # Layer 2: Rust AI shell
│   ├── Cargo.toml            # Dependencies
│   ├── src/
│   │   ├── main.rs          # REPL entry point
│   │   ├── lib.rs           # Core library
│   │   ├── parser.rs        # Command parser
│   │   ├── tools.rs         # Tool dispatch
│   │   └── tests/           # Rust integration tests
│   └── Makefile             # Build: cd shell && cargo build --release
│
├── bantu_os/                  # Layers 3 & 4: Python AI engine + services
│   ├── core/
│   │   ├── kernel/          # kernel.py, llm_manager.py, providers/
│   │   ├── socket_server.py # Unix socket + TCP dual-stack server
│   │   ├── scheduler.py     # Task scheduling
│   │   └── utils/           # Helper utilities
│   ├── agents/
│   │   ├── agent_manager.py # Multi-agent orchestration
│   │   ├── task_manager.py  # Task lifecycle management
│   │   ├── tool_executor.py # Async tool execution pipeline
│   │   └── tools/           # Built-in tools (browser, calculator, file, etc.)
│   ├── memory/
│   │   ├── chroma_store.py  # ChromaDB vector store
│   │   ├── knowledge_graph.py
│   │   ├── vector_db.py
│   │   └── embeddings/       # OpenAI embeddings
│   ├── services/
│   │   ├── file_service.py
│   │   ├── process_service.py
│   │   ├── network_service.py
│   │   ├── scheduler_service.py
│   │   ├── messaging/        # Phase 2: messaging service
│   │   ├── fintech/          # Phase 2: fintech service
│   │   └── crypto/           # Phase 2: crypto wallet service
│   ├── security/
│   │   ├── secrets.py        # Secrets management
│   │   └── sanitizer.py      # Input sanitization
│   └── interface/
│       ├── cli/              # CLI shell commands
│       └── hooks/           # Text/voice hooks
│
├── tests/
│   ├── unit/                 # Python unit tests
│   ├── integration/          # Python integration tests
│   ├── kernel/               # Kernel, socket, agentic loop tests
│   ├── memory/               # ChromaDB integration tests
│   └── services/             # Service-level tests
│
├── docs/                      # Architecture documentation
│   ├── SPEC.md              # This file (project truth)
│   ├── KERNEL.md            # Kernel design & protocol
│   ├── SECURITY.md          # Security model
│   └── TOOL_INTERFACE.md    # Tool executor interface spec
│
├── scripts/
│   └── dev-setup.sh         # Dev environment bootstrap
│
├── .github/workflows/
│   └── ci.yml              # GitHub Actions CI (pytest + cargo test)
│
├── AGENTS.md                # Agent team context & workflow
├── CONTRIBUTING.md          # Contribution guide
├── Makefile                 # Top-level build targets
└── start.sh                 # Full system launch script
```

---

## 5. Roadmap

```
Phase 1 — Foundation ✅  (COMPLETE)
├── ✅ C Init System — PID 1, service registry, signal handling
├── ✅ Rust Shell — REPL, natural language dispatch, 13 tests
├── ✅ Python AI Engine — Kernel, LLM manager, agentic loop, 43 tests
├── ✅ Python Services — FileService, ProcessService, NetworkService
├── ✅ Memory — ChromaDB persistent store, knowledge graph, embeddings
└── ✅ CI/CD — pytest + cargo test on every push/PR

Phase 2 — Connectivity 🔨  (IN PROGRESS)
├── Messaging integration (email, SMS, instant messaging)
├── Banking / fintech APIs
└── Crypto wallet integration

Phase 3 — Ecosystem
├── IoT smart device support
└── Hardware prototype

Phase 4 — Scale
├── Enterprise partnerships
└── Global rollout
```

---

## 6. Getting Started

### Prerequisites

- Linux (Debian/Ubuntu-based)
- Python 3.10+
- Rust 1.70+
- GCC
- Git

### Build & Run

```bash
# Clone
git clone https://github.com/MB-Ndhlovu/Bantu-Os.git
cd Bantu-Os

# Python environment
pip install -e .

# Build C init
cd init && make

# Build Rust shell
cd ../shell && cargo build --release

# Run tests
make test

# Quick launch (Python kernel REPL)
python main.py

# Full system (requires shell built)
./start.sh
```

### Troubleshooting

| Problem | Solution |
|---------|----------|
| `poetry: command not found` | `pip install poetry` |
| Rust build fails | `rustup update && rustup default stable` |
| GCC errors | `apt install build-essential` |
| Python import fails | `pip install -e .` |
| Tests fail | Ensure Python 3.10+ (`python3 --version`) |

---

## 7. Contribution Guidelines

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full guide.

### Commit Convention

```
<type>(<scope>): <description>
```

**Types:** `feat` | `fix` | `docs` | `test` | `refactor` | `chore`

**Examples:**
- `feat(init): add SIGTERM handling`
- `fix(scheduler): HHMM regex`
- `docs(kernel): add socket protocol section`

### Workflow

1. `git fetch upstream && git checkout main && git pull upstream main`
2. `git checkout -b feat/your-feature-name`
3. Make changes
4. `python -m pytest tests/ -v` — **all must pass**
5. `git add . && git commit -m "<type>(<scope>): description"`
6. `git push origin feat/your-feature-name`
7. Open PR on GitHub

### Code Review

- All PRs require review before merge
- Tests must pass in CI before merge
- Breaking changes to architecture require update to this document

---

## 8. Architecture Decision Log

| Decision | Date | Rationale |
|----------|------|-----------|
| C for init system | 2024 | PID 1 requires minimal runtime; direct kernel ABI access needed |
| Rust for shell | 2024 | Memory safety + no GC pause for interactive REPL |
| Python for AI engine | 2024 | Ecosystem (OpenAI, ChromaDB, embeddings) is Python-native |
| Unix socket for IPC | 2024 | Low-latency local IPC; TCP fallback for container/networked setups |
| ChromaDB for memory | 2024 | Mature, embeddable vector store with Python SDK |

---

*Last updated: 2026-04-17*
