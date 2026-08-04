# Bantu-OS — Project Status

**This is the single source of truth for project status.** README, AGENTS.md, and the docs subdirectory all point here when they need a current snapshot. Edit this file last when a task changes project state.

**Last Updated:** 2026-08-04

---

## Current Phase

**Phase 4 (CI, integrations, security reconciliation) in progress. The first public pre-alpha release, `v0.1.0`, is prepared from the verified `main` baseline.**

Working stack: Linux kernel → C init (PID 1) → Rust shell REPL → Python AI kernel + services. The canonical end-to-end demo boots the full stack and exercises the wired service bridge.

---

## Verification — 2026-08-04

| Gate | Result | Evidence |
|---|---|---|
| Python tests | ✅ Pass | `384 passed, 4 skipped, 16 warnings` via `python3 -m pytest tests/ -q --tb=short` |
| Rust tests | ✅ Pass | 13 library + 13 binary + 4 integration tests passed via `cd shell && cargo test --lib --tests` |
| C compilation | ✅ Pass | `cd init && make clean && make` with `-Wall -Wextra -Werror` |
| Ruff | ✅ Pass | `python3 -m ruff check bantu_os/ tests/` |
| Black | ✅ Pass | `python3 -m black --check bantu_os/ tests/` |
| Full-stack demo | ✅ Pass | `bash scripts/demo.sh`, all scripted checks completed successfully |
| Docker image | ⚠️ Pending runner | Local runner has neither Docker nor Podman; must be built on a Docker-capable runner |
| GitHub Actions | ⚠️ Blocked externally | GitHub reports the repository account is locked due to a billing issue; local equivalent gates passed |

The test suite emits 16 non-failing warnings: existing async-marker warnings, aiohttp application-key warnings in the new API test, socket-test coroutine warnings, and a constrained `/proc/vmstat` environment. They do not fail the gate.

---

## Security Review — 2026-08-03

**Re-run result:** security reconciliation completed for the release baseline.

- Unix socket permissions hardened from world-readable/writable `0666` to owner-only `0600`.
- API-key JSON persistence now uses an atomic temporary-file replacement and owner-only `0600` permissions.
- API-key creation now requires `Authorization: Bearer $BANTU_ADMIN_API_KEY`; verification remains the only unauthenticated API auth endpoint.
- Password hashing uses PBKDF2-HMAC-SHA256 with 600,000 iterations and constant-time digest comparison.
- No generated ChromaDB files or compiled binaries are included in the reconciled source change set.
- Known production gaps remain: HMAC/replay protection for IPC, full-disk encryption, TPM attestation, and a Docker-capable image build verification.

---

## What's Working

The following execute end-to-end against the live kernel/shell pair on a fresh demo boot:

| # | Capability | Source |
|---|------------|--------|
| 1 | Kernel ping / health check | `core/socket_server.py` |
| 2 | File service: read, write, copy, move, delete | `services/file_service.py` |
| 3 | Process service: list, system stats, existence | `services/process_service.py` |
| 4 | Network service: DNS, local IP, port check | `services/network_service.py` |
| 5 | Hardware service: CPU, memory, disk telemetry | `services/hardware/` |
| 6 | IoT service: device list, scan, telemetry | `services/iot/` |
| 7 | Messaging service: send, receive, channels | `services/messaging/` |
| 8 | Rust shell REPL: parse → dispatch → tool | `shell/src/` |
| 9 | Intent kernel streaming protocol | `core/intent/` |
| 10 | Authenticated network API | `api/` |

---

## What's Next

1. Build and run the Docker image on a Docker-capable runner, then exercise the container health check and boot path.
2. Keep the new regression tests for socket mode `0600`, private API-key persistence, admin-only API-key creation, and PBKDF2 password hashing in the mandatory CI gate.
3. Implement IPC authentication and replay protection before exposing the TCP listener beyond localhost.
4. Resolve the existing pytest async-marker warnings.
5. Continue Phase 4 integration-provider tests with credentials isolated from source control.

---

## Build & Test

```bash
python3 -m pytest tests/ -q --tb=short
cd shell && cargo test --lib --tests
cd ../init && make clean && make
cd .. && python3 -m ruff check bantu_os/ tests/
cd .. && python3 -m black --check bantu_os/ tests/
bash scripts/demo.sh
```

---

## Contribution Rules

- One status doc: this file.
- One demo: `scripts/demo.sh`.
- Do not commit ChromaDB runtime files, coverage output, Rust targets, or compiled C binaries.
- Run the Python, Rust, C, Ruff, Black, and demo gates before opening a PR.
