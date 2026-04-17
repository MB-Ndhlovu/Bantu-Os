# Bantu-OS Documentation

> Start with [SPEC.md](../SPEC.md) for the full project specification.

## Index

| Document | Description |
|----------|-------------|
| [SPEC.md](../SPEC.md) | **Project specification** — architecture, components, roadmap, contribution guidelines |
| [KERNEL.md](./KERNEL.md) | Kernel design — LLM manager, providers, agentic loop, socket protocol |
| [SECURITY.md](./SECURITY.md) | Security model — secrets, sanitization, privilege model |
| [TOOL_INTERFACE.md](./TOOL_INTERFACE.md) | Tool executor interface — service protocol, tool schema |

## Architecture Overview

```
Layer 4: Services (Python) — file, process, network, scheduler, messaging, fintech, crypto
Layer 3: AI Engine (Python) — kernel, llm_manager, tool_executor, agent_manager
Layer 2: Shell (Rust) — REPL, command parser, tool dispatcher
Layer 1: Init (C) — PID 1, service registry, signal handling
BASE:    Linux Kernel
```

## Quick Links

- [CONTRIBUTING.md](../CONTRIBUTING.md) — Dev setup, testing, PR process
- [AGENTS.md](../AGENTS.md) — Agent team workflow & priorities
- [README.md](../README.md) — Project overview & quick start
