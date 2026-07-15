# Bantu-OS — Project Status

**This is the single source of truth for project status.** README, AGENTS.md, and the docs subdirectory all point here when they need a current snapshot. Edit this file last when a task changes project state.

**Last Updated:** 2026-07-13

---

## Current Phase

**Phase 3 (Service Manager) + Phase 4 (Network & Integration Services)** in progress.

Working stack: Linux kernel → C init (PID 1) → Rust shell REPL → Python AI kernel + services. The end-to-end demo `bash scripts/demo.sh` boots the full stack and exercises every wired service.

---

## What's Working (verified by `bash scripts/demo.sh`)

The following execute end-to-end against the live kernel/shell pair on a fresh boot:

| # | Capability | Source |
|---|------------|--------|
| 1 | Kernel ping / health check | `core/socket_server.py` |
| 2 | File service: read, write, copy, move, delete | `services/file_service.py` |
| 3 | Process service: list, system stats, existence | `services/process_service.py` |
| 4 | Network service: DNS, local IP, port check | `services/network_service.py` |
| 5 | Hardware service: CPU, memory, disk telemetry | `services/hardware/` |
| 6 | IoT service: device list, scan, telemetry | `services/iot/` |
| 7 | Messaging service: send, receive, channels | `services/messaging/` |
| 8 | AI service: provider status, route listing | `ai/service.py` |
| 9 | Auth service: session create/get/list/destroy | `auth/service.py` |
| 10 | Rust shell REPL: parse → dispatch → tool | `shell/src/` |
| 11 | Rust integration tests: full stack boot | `shell/src/tests/integration_tests.rs` |

**Demo command:** `bash scripts/demo.sh` (~30s, no setup). 11/11 endpoints green.

---

## Module Inventory

**Rust shell** (`shell/`): parser, dispatch, REPL, tool exec, 4 integration tests.

**Python kernel** (`bantu_os/core/`): socket server, kernel loop, intent kernel, memory.

**Services** (`bantu_os/services/`, 16 modules):
- Tier 1: `file_service`, `process_service`, `network_service`
- Domain: `hardware`, `iot`, `messaging`, `crypto`, `fintech`
- Platform: `service_base`, `supervisor`, `scheduler_service`
- Special: `sandboxed_file_service`

**Agents** (`bantu_os/agents/`): `base_agent`, `agent_manager`, `scheduling_agent`.

**AI** (`bantu_os/ai/`): `service`, `agent`, `tools/`.

**Auth** (`bantu_os/auth/`): session service.

---

## Test Inventory

- **Rust:** 4 integration tests in `shell/src/tests/integration_tests.rs` (`cargo test`).
- **Python unit:** 23 files under `tests/unit/` covering scheduling, knowledge graph, CLI server, services, file, shell, scheduler, LLM manager, Chroma store, smoke.
- **Python kernel:** 5 files under `tests/kernel/` — kernel core, socket server, async tool pipeline, agentic loop, integration.
- **Python intent:** 3 files under `tests/intent/` — goal tree, goal planner, intent kernel.
- **Python agent:** `tests/agent/test_agent_manager.py`.
- **Python memory:** `tests/memory/test_chroma_integration.py`.
- **Python integration:** `tests/integration/test_init.py`, `tests/integration/test_shell.py`, `tests/test_e2e_full.py`, `tests/test_e2e_shell_kernel.py`, `tests/test_engine.py`.

**Total: 330 test functions across the suite.**

---

## What's Next (in priority order)

1. **Boot the full stack as a single command** — `scripts/demo.sh` does this, but the Rust shell + Python kernel + services trio needs hardening for non-interactive CI runs.
2. **CI pipeline** — add `cargo test` to GitHub Actions; the Python side is already covered by `pytest`.
3. **Llm_manager parity test** — the unit test exists; the integration with the AI service async pipeline does not.
4. **ChromaDB memory integration** — module exists; embeddings are stubbed.
5. **Architecture decision records** — start an `docs/adr/` folder for the next layer of decisions (multi-user, persistence, persistence model).

---

## Build & Test

```bash
# Full demo
bash scripts/demo.sh

# Rust
cd shell && cargo build && cargo test

# Python
python -m pytest tests/ -v
```

---

## Contribution Rules

- **One status doc.** This file. When work is done, update the "What's Working" or "What's Next" section here. Do not add new top-level status files. README/AGENTS link to this file.
- **One demo.** `scripts/demo.sh` is the canonical proof that the stack works. If you change a service, re-run it. If it goes red, fix before merging.
- **One test command per layer.** Rust: `cargo test`. Python: `pytest tests/`. Don't add parallel test runners.
