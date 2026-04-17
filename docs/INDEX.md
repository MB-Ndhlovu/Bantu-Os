# Bantu-OS Documentation Index

Welcome to the Bantu-OS documentation.

## 📚 Documentation Map

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACE                        │
│         (Shell, CLI, voice — user's entry point)        │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                      LAYER 4 — Services                  │
│         bantu_os/services/  (Python)                    │
├─────────────────────────────────────────────────────────┤
│                      LAYER 3 — AI Engine                 │
│         bantu_os/core/kernel/  (Python)                  │
├─────────────────────────────────────────────────────────┤
│                      LAYER 2 — Shell                     │
│         shell/src/main.rs  (Rust)                        │
├─────────────────────────────────────────────────────────┤
│                      LAYER 1 — Init                      │
│         init/init.c  (C, PID 1)                         │
├─────────────────────────────────────────────────────────┤
│                  LINUX KERNEL (Base)                    │
└─────────────────────────────────────────────────────────┘
```

## 📄 Core Specs

| Document | Description |
|----------|-------------|
| [SPEC.md](./SPEC.md) | **Start here.** Full project specification: architecture, language choices, directory layout, roadmap, contribution guidelines. |
| [KERNEL.md](./KERNEL.md) | Layer-by-layer kernel architecture: C init → Rust FFI → Python services. Covers boot sequence and IPC design. |
| [SECURITY.md](./SECURITY.md) | Threat model, privilege tiers, secrets management, input sanitization, IPC security, boot integrity. |
| [INIT.md](./INIT.md) | C init system design: service registry, signal handling, dependency resolution. |
| [SHELL.md](./SHELL.md) | Rust AI shell design: REPL, command parser, tool dispatch protocol. |

## 🔧 Architecture Notes

### Languages by Layer

| Layer | Language | Why |
|-------|----------|-----|
| Init (PID 1) | C | Direct kernel interaction, minimal footprint, no runtime dependencies |
| Shell | Rust | Memory safety, performance, expressive enough for complex logic |
| AI Engine + Services | Python | Rapid iteration, rich ecosystem (LLM clients, vector DB, web frameworks) |

### Directory Map

```
bantu_os/
├── init/              → Layer 1: C init system (PID 1)
├── shell/             → Layer 2: Rust AI shell
├── bantu_os/
│   ├── core/          → Layer 3: AI engine (kernel, llm_manager)
│   ├── agents/        → Agent loop, tool executor, task manager
│   ├── memory/        → Vector DB, knowledge graph, embeddings
│   ├── services/      → Layer 4: File, process, network, scheduler
│   ├── security/      → Secrets management
│   └── interface/     → CLI shell, voice/text hooks
├── tests/             → Unit + integration tests
└── docs/              → This directory
```

## 🚀 Quick Reference

### Build All Layers
```bash
# Python AI engine
pip install -e .

# C init
cd init && make

# Rust shell
cd ../shell && cargo build --release

# Run tests
python -m pytest tests/ -v
```

### Commit Convention
```
<type>(<scope>): <description>
Types: feat | fix | docs | test | refactor | chore
```

### Key Files
- `AGENTS.md` — Agent team workflow and priorities
- `CONTRIBUTING.md` — How to set up dev environment and submit PRs
- `Makefile` — Root build orchestration

## 📅 Roadmap

| Phase | Focus |
|-------|-------|
| Phase 1 (current) | Foundation — working init, shell, Python AI engine, basic services |
| Phase 2 | Connectivity — messaging, fintech APIs, crypto wallet basics |
| Phase 3 | Ecosystem — IoT device support, hardware prototypes |
| Phase 4 | Scale — enterprise partnerships, global rollout |

## 🔗 External Links

- [GitHub Repository](https://github.com/MB-Ndhlovu/Bantu-Os)
- [Open Issues](https://github.com/MB-Ndhlovu/Bantu-Os/issues)
- [License](../LICENSE)
