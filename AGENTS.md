# Bantu-OS — Agent Working Context

**Repo:** https://github.com/MB-Ndhlovu/Bantu-Os
**Branch:** main
**Auth:** GITHUB_TOKEN stored in Zo secrets (never expose in code or chat)

## Architecture

Bantu-OS is a Linux-based AI-native OS. Built with C (init), Rust (shell), Python (AI engine).

```
Layer 4: Services (Python) — file, process, network services
Layer 3: AI Engine (Python) — kernel, llm_manager, tool_executor
Layer 2: Shell (Rust) — REPL, command parser, tool dispatch
Layer 1: Init (C) — PID 1, service registry, signal handling
BASE:    Linux Kernel
```

## Current Project State

- C init: ✅ Compiles and works (init/init.c)
- Rust shell: ✅ Builds (shell/src/main.rs, shell/Cargo.toml), 13 tests passing
- Python AI engine: ✅ Kernel, LLM manager, agentic loop, 43 tests passing
- ChromaDB memory: ✅ Persistent vector store, 9 tests passing
- Services: ✅ FileService, ProcessService, NetworkService
- CI: ✅ pytest + cargo test on every push/PR
- **Phase 2 (skeleton): 🔨 Messaging/Fintech/Crypto services — architecture defined, stubs created**

## Workflow (Mandatory for All Agents)

```
1. git fetch upstream
2. git checkout main && git pull upstream main
3. git checkout -b feat/your-feature-name
4. Make changes
5. python -m pytest tests/ -v  (ALL must pass)
6. git add . && git commit -m "<type>(<scope>): description"
7. git push origin feat/your-feature-name
8. Open PR on GitHub
```

## What to Build Next (Priority Order)

1. ~~Shell-to-kernel socket connection (Rust shell → Python kernel over Unix socket)~~ ✅ DONE
   - `bantu_os/core/socket_server.py` — dual Unix socket (`/tmp/bantu.sock`) + TCP (`127.0.0.1:18792`)
   - `tests/kernel/test_socket_server.py` — 18 integration tests passing
   - Tool protocol: `{"cmd": "tool", "tool": "file|process|network", "method": "method_name", "args": {...}}`
   - AI protocol unchanged: `{"cmd": "ai", "text": "..."}`
   - Remaining: end-to-end test with real Rust shell binary + kernel boot via `start.sh`
2. AI-native shell UX (polish REPL, history, tab completion)
3. C init integration (service registry wiring into the C init system)
4. Phase 2: Connectivity (messaging, fintech APIs, crypto wallet)

## Commit Convention

`<type>(<scope>): <description>`

Types: feat | fix | docs | test | refactor | chore
Examples: `feat(init): add SIGTERM handling`, `fix(scheduler): HHMM regex`

## Important

- NEVER expose GITHUB_TOKEN in code or messages
- All tests must pass before pushing
- Read SPEC.md before working on architecture-level changes