# Bantu-OS — Agent Working Context

**Repo:** https://github.com/MB-Ndhlovu/Bantu-Os
**Remote:** origin (authenticated via GITHUB_TOKEN in Zo secrets)
**Branch:** main

**Auth setup:**
```bash
git remote set-url origin https://x-access-token:${GITHUB_TOKEN}@github.com/MB-Ndhlovu/Bantu-Os.git
git config credential.helper "store"
```

## Project Structure

```
bantu_os/
├── bantu_os/
│   ├── core/kernel/       # LLM manager, providers, kernel
│   ├── agents/           # SchedulingAgent, TaskManager, base_agent
│   ├── memory/           # Vector DB, knowledge graph
│   ├── interface/        # CLI shell, hooks
│   └── config/           # Settings
├── tests/
│   ├── unit/             # Unit tests (passing)
│   └── kernel/           # Kernel tests
└── pyproject.toml
```

## Phase Roadmap

- Phase 1: OS Core + AI Assistant MVP ← CURRENT
- Phase 2: Connectivity (messaging, banking, crypto)
- Phase 3: IoT ecosystem
- Phase 4: Enterprise + global rollout

## Current Status (as of 2026-04-16)

- 6 commits on main, early-stage foundation
- Tests: scheduling_agent (30 passing), task_manager (8 passing), llm_manager (11 passing)
- Missing: kernel tests, memory tests, integration tests
- Missing: CLI commands, shell integration, real API keys in providers

## Agent Team

| Agent | Role | Time |
|-------|------|------|
| Midnight Coder | Full codebase, 1.5hrs/day | 00:00 |
| Memory Engineer | ChromaDB, embeddings | 01:00 |
| CLI Engineer | Shell, commands | 03:00 |
| Testing Lead | Test coverage | 05:00 |
| Kernel Engineer | System services, agent pipeline | 07:00 |
| Integration Lead | APIs, fintech, crypto | 09:00 |
| Social (AM) | Twitter updates | 07:00 |
| Social (PM) | Twitter updates | 12:00 |
| Docs Writer | README, CONTRIBUTING | 15:00 |

## Pull-Push Workflow

Every agent that makes changes must:
1. `git pull origin main` — always start fresh
2. Make changes
3. `git add . && git commit -m "descriptive message"`
4. `git push origin main`

If push fails with "Authentication error", the GITHUB_TOKEN may have expired. Notify the supervisor.
