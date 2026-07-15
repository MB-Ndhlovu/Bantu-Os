# Bantu-OS — Agent Working Context

**Repo:** https://github.com/MB-Ndhlovu/Bantu-Os
**Branch:** main
**Auth:** GITHUB_TOKEN stored in Zo secrets (never expose in code or chat)

**For project status, read [STATUS.md](./STATUS.md).** This file is workflow + rules only.

## Architecture

Bantu-OS is a Linux-based AI-native OS. Built with C (init), Rust (shell), Python (AI engine + services).

```
Layer 4: Services (Python) — file, process, network, hardware, iot, messaging, crypto, fintech
Layer 3: AI Engine (Python) — kernel, llm_manager, tool_executor, agents
Layer 2: Shell (Rust) — REPL, command parser, tool dispatch
Layer 1: Init (C) — PID 1, service registry, signal handling
BASE:    Linux Kernel
```

## Workflow (Mandatory)

```
1. git fetch upstream
2. git checkout main && git pull upstream main
3. git checkout -b feat/your-feature-name
4. Make changes
5. python -m pytest tests/ -v  (ALL must pass)
6. bash scripts/demo.sh        (full stack must stay green)
7. git add . && git commit -m "<type>(<scope>): description"
8. git push origin feat/your-feature-name
9. Open PR on GitHub
```

After merging, update [STATUS.md](./STATUS.md) — that's the only status doc.

## Intent Kernel Quick Start

- `bantu_os/core/intent/` — package implementation
- `docs/INTENT_KERNEL.md` — companion design doc

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

## Rules

- NEVER expose GITHUB_TOKEN in code or messages
- All tests must pass before pushing (`pytest tests/ -v` + `cargo test`)
- `bash scripts/demo.sh` must stay green — that's the contract for the full stack
- Read `STATUS.md` before working on architecture-level changes
- One status doc (STATUS.md). One demo script (`scripts/demo.sh`). Don't add parallel trackers.

## What to Build Next (Priority Order)

1. Shell ↔ kernel Unix socket bridge — verify end-to-end (`bantu_os/core/socket_server.py` exists; confirm it is wired to `shell/src` and passes an integration test, not just unit tests in isolation)
2. C init ↔ service registry wiring
3. Live-provider integration test for at least one Phase 2/3 service (suggest: Telegram bot, lowest setup cost) before calling that phase done
4. AI-native shell UX polish (REPL history, tab completion)
