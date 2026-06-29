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
- Python AI engine: ✅ Kernel, LLM manager, agentic loop, 43+ tests passing
- ChromaDB memory: ✅ Persistent vector store, 9 tests passing
- Services: ✅ FileService, ProcessService, NetworkService
- Init bridge: ✅ InitBridge for C init service registry, registered with C init on boot
- CI: ✅ pytest + cargo test on every push/PR
- Intent Kernel: ✅ Phase 1 + 2 + 3 — `bantu_os/core/intent/`, streaming socket protocol,
  Rust shell routes AI mode through the kernel, 10 intent unit tests + 4 socket-level
  intent tests passing
- **Phase 4 (in progress):** Scaling, integrations, polish

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

## Intent Kernel Quick Start

- `bantu_os/core/intent/` — package implementation
- `docs/INTENT_KERNEL.md` — companion design doc
- `bantu_os_intent_kernel_spec.docx` — original spec

```python
from bantu_os.core.intent import IntentKernel, GoalPlanner
from bantu_os.agents.agent_manager import AgentManager

agent = AgentManager(kernel=kernel)
planner = GoalPlanner(llm_manager=kernel.llm, available_tools=agent.tools.keys())
intent = IntentKernel(agent_manager=agent, planner=planner)
result = await intent.receive("deploy the project")
```

Socket protocol (added alongside the existing JSON line protocol):
- `{"cmd": "intent", "text": "...", "stream": true}` — submit goal
- `{"cmd": "confirm", "step_id": "...", "decision": "approve"}` — reply to gate
- frames: `goal_update`, `confirmation_required`, `goal_complete`, `goal_failed`

## Commit Convention

`<type>(<scope>): <description>`

Types: feat | fix | docs | test | refactor | chore
Examples: `feat(init): add SIGTERM handling`, `fix(scheduler): HHMM regex`

## Important

- NEVER expose GITHUB_TOKEN in code or messages
- All tests must pass before pushing
- Read SPEC.md and docs/INTENT_KERNEL.md before working on architecture-level changes
