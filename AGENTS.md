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
- Rust shell: ✅ Builds (shell/src/main.rs, shell/Cargo.toml)
- Python AI engine: 🔨 Core exists, needs kernel tests
- Tests: scheduling_agent (passing), task_manager (passing), llm_manager (passing)

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

1. Rust shell tool dispatch (shell/src/main.rs → parse.rs)
2. Python kernel integration tests
3. Python service APIs (file, process, network)
4. ChromaDB memory integration
5. CI: add cargo test
6. Architecture docs (SPEC.md already done)

## Commit Convention

`<type>(<scope>): <description>`

Types: feat | fix | docs | test | refactor | chore
Examples: `feat(init): add SIGTERM handling`, `fix(scheduler): HHMM regex`

## Important

- NEVER expose GITHUB_TOKEN in code or messages
- All tests must pass before pushing
- Read SPEC.md before working on architecture-level changes