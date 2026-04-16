# Bantu-OS

**The African-born, AI-native operating system built on Linux.**

Bantu-OS is a Linux-based, AI-native operating system that reimagines how humans interact with technology — putting a personal AI assistant at the core of the experience. Built from first principles using C, Rust, and Python, it runs as a layer on top of Linux, combining the stability of a proven kernel with intelligent, adaptive computing.

> 🌍 *"The next great platform shift won't come from Silicon Valley. It will come from those who build for the realities of tomorrow."*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Pre-alpha](https://img.shields.io/badge/Status-Pre--alpha-red)](README.md)
[![Architecture: Linux-based](https://img.shields.io/badge/Arch-Linux--based-brightgreen)](README.md)
[![Language: C + Rust + Python](https://img.shields.io/badge/Lang-C%2C%20Rust%2C%20Python-yellow)](README.md)

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
| AI Shell | Rust | 🔨 In Progress | REPL with tool dispatch, rustyline editor |
| AI Engine | Python | 🔨 In Progress | LLM manager, kernel, tool executor |
| Services | Python | 🔨 In Progress | File, process, network, scheduler services |
| Memory | Python | 🔨 In Progress | Vector DB, knowledge graph, embeddings |

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
├── bantu_os/                # Layer 3 & 4: Python AI engine
│   ├── core/
│   │   └── kernel/          # LLM manager, providers, kernel
│   ├── agents/              # Task manager, scheduler, tools
│   ├── memory/              # Vector DB, knowledge graph
│   ├── services/           # File, process, network services
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

## 🚀 Quick Start

### Prerequisites

- Linux (Debian/Ubuntu-based)
- Python 3.10+ with `venv`
- Rust 1.70+
- GCC
- Git
- Docker (optional, for containerized build)

### Build & Run

```bash
# Clone the repository
git clone https://github.com/MB-Ndhlovu/Bantu-Os.git
cd Bantu-Os

# One-command setup (installs all Python dependencies)
make install

# Build all layers using the root Makefile
make build        # Python package

# Layer 1: Build C init system
cd init && make

# Layer 2: Build Rust shell
cd ../shell && cargo build --release

# Back to root
cd ..

# Verify everything works
make test         # Run Python test suite
./shell/target/release/bantu  --help  2>/dev/null && echo "Rust shell: OK"
python -c "import bantu_os; print('Python engine: OK')"  # Verify Python import
```

### Docker (Optional)

```bash
# Build Docker image
make docker-build

# Run inside container
make docker-run
```

### Troubleshooting

| Problem | Solution |
|---------|----------|
| `poetry: command not found` | `pip install poetry` |
| Rust build fails | `rustup update && rustup default stable` |
| GCC compilation errors | `apt install build-essential` |
| Python import fails | `make install` to reinstall dependencies |
| Tests fail | Check Python version is 3.10+ with `python3 --version` |

---

## 📦 What's Implemented

| Component | Status | Notes |
|-----------|--------|-------|
| C Init System | ✅ | Compiles, service registry, PID 1 ready |
| Rust Shell | ✅ | REPL skeleton, tool dispatch foundation |
| Python AI Engine | 🔨 | LLM manager, Kernel, OpenAI provider |
| Tool Executor | 🔨 | Dynamic tool loading, async pipeline |
| Vector DB | 🔨 | In-memory, cosine similarity search |
| Knowledge Graph | 🔨 | In-memory triples, traversal |
| Secrets Manager | 🔨 | Basic encrypted store |
| CI/CD | ✅ | GitHub Actions workflow |
| Tests | 🔨 | Unit tests for scheduling, task manager, LLM |

---

## 🗺️ Roadmap

```
Phase 1 — Foundation (Current)
├── ✅ C Init System
├── ✅ Rust Shell skeleton
├── 🔨 Python AI Engine
├── 🔨 Python Services
└── 🔨 Memory layer

Phase 2 — Connectivity
├── Messaging integration
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