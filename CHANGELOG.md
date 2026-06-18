# Changelog

All notable changes to Bantu-OS are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]
### In Progress
- Phase 4: Intent Kernel — natural-language goals, goal trees, monitoring, retry, confirmation
  - `bantu_os/core/intent/` package: `intent_kernel.py`, `goal_planner.py`, `goal_tree.py`,
    `execution_monitor.py`, `retry_engine.py`, `confirmation_gate.py`, `intent_renderer.py`
  - Socket protocol `cmd: "intent"` (single-shot + streaming `stream: true`) and `cmd: "confirm"`
  - Shell routes AI-mode input through the intent kernel
  - 10 intent unit tests + 4 socket-level intent tests passing
  - See `INTENT_KERNEL.md` for the full design.

- Raspberry Pi hardware prototype
- AI shell UX polish (history, tab completion)
- C init ↔ Python service registry wiring

---

## [0.3.0] — Phase 3: Ecosystem
### Added
- IoT: MQTT broker client, device registry, sensor ingestion
- Hardware monitoring: CPU, RAM, disk, network, GPIO, USB
- Multi-user sessions with isolated AI contexts, token budgets, tool permissions
- ServiceManager: discover, start/stop, health checks, auto-restart, event hooks

---

## [0.2.0] — Phase 2: Connectivity
### Added
- Messaging: email (SMTP), SMS via Twilio, Telegram bot
- Fintech: Stripe, M-Pesa STK push, Flutterwave, Paystack
- Crypto: ETH/ERC-20 multi-chain wallet (balance, send, sign)

---

## [0.1.0] — Phase 1: Foundation
### Added
- C Init System: PID 1, service registry, signal handling
- Rust AI Shell: REPL, natural language dispatch, tool dispatch, 13 tests
- Python AI Engine: kernel, LLM manager, OpenAI provider, agentic loop
- Python Services: FileService, ProcessService, NetworkService
- Memory: ChromaDB persistent store, knowledge graph, embeddings
- CI/CD: GitHub Actions (pytest + cargo test on every push/PR)
- 97 Python tests + 13 Rust tests passing