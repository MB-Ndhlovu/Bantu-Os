# Bantu-OS Changelog

Historical log of completed work. For current status see [STATUS.md](./STATUS.md).

## 2026-07-13

- Realigned: STATUS.md is the single source of truth; PROGRESS.md is changelog only
- Added `scripts/demo.sh` as the contract for the full stack
- Verified end-to-end: 11/11 steps green on the live machine
- Added web UI at https://autoprime.zo.space/bantu-os

## 2026-05-13

- Intent Kernel Phase 1+2+3 merged
- Streaming socket protocol
- Rust shell routes AI mode through the kernel
- 10 intent unit tests + 4 socket-level intent tests passing
- InitBridge registered with C init on boot

## 2026-04-17

- Rust shell tool dispatch fix (`show`, `where`, `cd`)
- Python kernel integration tests (14 new)
- ChromaDB memory integration (9 new tests, persistent vector store)
- CI: cargo test step added to GitHub Actions
- Agentic loop: LLM → tool call → execute → re-prompt

Total tests: 326 Python + 4 Rust. See STATUS.md for current numbers.
