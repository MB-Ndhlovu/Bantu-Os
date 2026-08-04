# Changelog

All notable changes to Bantu-OS are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Planned

- IPC authentication and replay protection before exposing the TCP listener beyond localhost
- Docker-capable image build and boot verification
- Raspberry Pi hardware prototype
- Additional live-provider integration tests with credentials isolated from source control
- Resolution of the remaining pytest async-marker warnings

---

## [0.1.0] — 2026-08-04

**First public pre-alpha release.** This release establishes the working cross-layer foundation of Bantu-OS: a Linux-based, AI-native operating-system layer built with C, Rust, and Python.

### Added

- C init system with PID 1 lifecycle management, signal handling, service registry, and registry socket wiring
- Rust AI shell with REPL history, tab completion, natural-language command parsing, tool dispatch, and Unix-socket bridge
- Python AI engine with kernel, LLM manager, provider abstraction, agentic loop, memory, and knowledge graph
- Intent kernel with goal planning, execution monitoring, retries, confirmation gates, and streaming socket frames
- File, process, network, hardware, IoT, messaging, fintech, and crypto service layers
- Authenticated network API with API-key management and password hashing
- ChromaDB-backed persistent vector memory
- One-command full-stack demo via `bash scripts/demo.sh`
- MIT licensing, contributor guidance, architecture documentation, and GitHub Actions quality gates

### Verification

- Python: `384 passed, 4 skipped`
- Rust: 13 library tests, 13 binary tests, and 4 integration tests passed
- C init: compiled with `-Wall -Wextra -Werror`
- Ruff and Black checks passed
- Full-stack demo completed successfully

### Known limitations

- This is a pre-alpha developer release, not a production operating system image
- External provider integrations require user-supplied credentials and live-provider coverage is still expanding
- Docker image verification is pending a Docker-capable runner
- GitHub Actions was unavailable during release preparation because the repository account was locked by a billing issue; equivalent local gates passed

---

## Future roadmap

### 0.2.0 — Connectivity

- Messaging: email (SMTP), SMS via Twilio, and Telegram bot
- Fintech: Stripe, M-Pesa STK push, Flutterwave, and Paystack
- Crypto: ETH/ERC-20 multi-chain wallet operations

### 0.3.0 — Ecosystem

- IoT: MQTT broker client, device registry, and sensor ingestion
- Hardware monitoring: CPU, RAM, disk, network, GPIO, and USB
- Multi-user sessions with isolated AI contexts, token budgets, and tool permissions
- ServiceManager discovery, health checks, auto-restart, and event hooks

[Unreleased]: https://github.com/MB-Ndhlovu/Bantu-Os/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/MB-Ndhlovu/Bantu-Os/releases/tag/v0.1.0
