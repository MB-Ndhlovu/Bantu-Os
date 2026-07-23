# Agent 3 — AI Engine / Agent Lead Handoff

**Run date:** 2026-07-23 (Africa/Johannesburg)
**BLOCKER: YES**

## Gate

- `reports/01-systems-init-lead.md`: present for 2026-07-23 and **BLOCKER: NO**.
- `reports/02-rust-shell-engineer.md`: present for 2026-07-23 and **BLOCKER: NO**.
- Prerequisite gate: **PASSED**.

## Scope reviewed

Read `README.md`, `AGENTS.md`, `STATUS.md`, both prerequisite handoffs, the AI-engine kernel and agent modules, the socket-server protocol, and the Rust shell dispatch path. Changes were restricted to the AI-engine scope; Agent 1 and Agent 2 working-tree changes were preserved.

## Cross-layer interface verification

The active Rust shell ↔ Python socket path matches Agent 2's handoff:

- Rust sends newline-delimited JSON `{\"cmd\":\"tool\",\"tool\":\"file\",\"method\":\"read\",\"args\":{...}}` over `/tmp/bantu.sock`.
- `bantu_os/core/socket_server.py` resolves the registered service, calls the named method with keyword args, and returns one newline-delimited JSON response.
- The canonical demo confirmed the live `file.read`, `process.list_processes`, `network.ping`, hardware, and IoT paths.

A separate architectural mismatch remains: `bantu_os/agents/tool_executor.py` exposes dotted tool names such as `file.read` and returns `{success, result}` / `{success, error}`, while the Rust socket contract uses separate `tool` + `method` fields and the socket server's `{ok, result}` / `{ok, error}` response shape. `ToolExecutor` is not wired into the socket-server dispatch path, so this is not a failure of the active Rust bridge, but it must be resolved before treating the standalone agent executor as the shared cross-layer executor.

## Agentic-loop review and change

`bantu_os/core/kernel/kernel.py` now rejects malformed tool-call records before dispatching them:

- non-object calls;
- missing or non-string tool names;
- non-object `args` values.

These failures are returned as structured per-call errors, preserving the loop and allowing later valid calls to run. Unknown tools and tool exceptions continue to propagate as structured outcomes rather than crashing the loop. No memory/RAG, services, integrations, Rust, C, or unrelated documentation files were modified by Agent 3.

## Verification

From `/home/workspace/bantu_os`:

```text
make test
```

**FAIL — exit 2.** Python target: **371 passed, 1 failed, 7 skipped, 14 warnings** in 22.76s. The sole failure was `tests/unit/test_network_service.py::TestNetworkService::test_http_get_success`: `https://httpbin.org/get` returned HTTP 503 on one run and timed out after 10.026s on the final run. The failure is an external-network/test-environment issue outside Agent 3 ownership. Because the repository's mandatory full test gate is red, this handoff is marked **BLOCKER: YES**. Rust and C targets were not reached by `make test` after the Python failure.

AI-engine ownership tests:

```text
python -m pytest tests/kernel tests/agent tests/unit/test_agent_manager.py tests/unit/test_llm_manager.py tests/test_engine.py -q
```

**PASS — 110 passed, 0 failed, 4 warnings in 7.36s.** Warnings are existing `RuntimeWarning`s from mocked socket protocol tests: an `AsyncMock` coroutine is not awaited in `socket_server.py:499`.

Rust verification:

```text
cd shell && cargo test --lib --tests
```

**PASS — 30 passed, 0 failed**: 13 library tests, 13 binary tests, and 4 integration tests. Existing dead-code warnings remain.

C verification:

```text
cd init && make clean && make
```

**PASS** with `-Wall -Wextra -Werror -std=c11`, zero errors.

Canonical full-stack verification:

```text
bash scripts/demo.sh
```

**PASS — exit 0.** All demonstrated bridge/service checks completed, including Rust shell connectivity.

```text
python -m compileall -q bantu_os/core/kernel bantu_os/agents
git diff --check
```

**PASS.** Owned Python modules compile and no whitespace errors were found.

## Files touched / current diff scope

Agent 3 AI-engine diff:

- `bantu_os/core/kernel/kernel.py`
- `reports/03-ai-engine-lead.md`

Other current working-tree changes belong to prerequisite agents and were preserved:

- `init/init.c`
- `init/services.c`
- `shell/src/main.rs`
- `shell/src/parser.rs`
- other report files under `reports/`

Generated binaries and ChromaDB test mutations were restored and are not part of this handoff.

## Instructions for Agent 4

1. Treat this as a blocked handoff until the full `make test` gate is green; rerun the external `httpbin.org` test when network availability is stable, and escalate the test's external dependency to the owning services/test maintainer rather than changing memory/RAG code to mask it.
2. Preserve the AI-engine validation change and the distinction between the active socket bridge contract and the standalone `ToolExecutor` mismatch.
3. Do not claim the shared tool-executor interface is unified: an adapter or explicit contract decision is still required before `bantu_os/agents/tool_executor.py` can be treated as the Rust shell's executor.
4. The four socket-test `AsyncMock` warnings are non-blocking cleanup items for the socket-server/test owner; do not alter memory/RAG scope to address them.
