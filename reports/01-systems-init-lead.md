# Agent 1 — Systems/Init Lead Handoff

**Run date:** 2026-07-23 (Africa/Johannesburg)
**BLOCKER: NO**

## Reviewed and changed

Reviewed `README.md`, `AGENTS.md`, `STATUS.md`, `docs/INIT.md`, `init/Makefile`, and the C init layer covering PID 1 startup, signal masking/waiting, shutdown, service registration, lifecycle management, child reaping, config parsing, and service state reporting.

Changed only the init ownership scope:

- `init/services.c`
  - Deep-copy registered service arguments so registry entries do not borrow caller-owned strings.
  - Validate argument counts and argument pointers during registration.
  - Reject duplicate service names and null lookup/unregister names.
  - Free service arguments consistently on unregister, registry cleanup, and parser failure paths.
  - Stop a running service before unregistering it.
  - Harden `stop_service()` against invalid PIDs.
  - Return `UNKNOWN` for invalid service states instead of indexing outside the state-name table.
  - Reject overlong config argument lists instead of silently truncating them.
- `init/init.c`
  - Return from `shutdown_system()` when `reboot(RB_POWER_OFF)` fails instead of entering an uninterruptible `pause()` loop.

## Files touched

- `init/init.c`
- `init/services.c`
- `reports/01-systems-init-lead.md`

No Rust, Python, integration, or unrelated documentation files were modified.

## Verification

From `/home/workspace/bantu_os`:

```text
cd init && make clean && make
```

Result: PASS. GCC command completed with `-Wall -Wextra -Werror -std=c11`; zero warnings and zero errors.

```text
cd init && make test
```

Result: PASS. All service registry tests passed, including registry init, registration, lookup, callbacks, config parsing, and state transitions.

```text
git diff --check
```

Result: PASS. No whitespace errors.

Final working-tree scope check: only `init/init.c`, `init/services.c`, and this report are changed/untracked. Generated init binaries were restored so they are not part of the handoff.

## Open issues / blockers

- No build, test, or security blocker was found in the reviewed init scope.
- The existing init implementation still contains broader design limitations not changed here: service startup is grouped by priority rather than numerically sorted within each group; PID 1 startup paths use hard-coded shell locations; and `start_service()` marks a child `RUNNING` before it has successfully `execve()`d. These are follow-up items, not blockers for Agent 2's work.

## Instructions for Agent 2

Proceed with the next maintenance stage only after confirming this report exists and is marked `BLOCKER: NO`. Preserve the init-layer changes above. Do not assume a service is healthy solely because `start_service()` returned success; validate runtime readiness or exit status where your scope requires it.
