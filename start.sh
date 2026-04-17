#!/bin/bash
# Bantu-OS Boot Launcher
# Starts Python kernel server first, then the Rust shell connects automatically.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
KERNEL_DIR="$PROJECT_ROOT"
SHELL_BIN="$PROJECT_ROOT/shell/target/release/bantu"
SOCKET_PATH="/tmp/bantu.sock"
TCP_PORT=18792
PYTHON_KERNEL="bantu_os.core.socket_server"
KERNEL_LOG="/tmp/bantu-kernel.log"
MAX_WAIT_SECONDS=15

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[boot]${NC} $*"; }
warn() { echo -e "${YELLOW}[boot]${NC} WARNING: $*"; }
die()  { echo -e "${RED}[boot]${NC} ERROR: $*  (see $KERNEL_LOG)" >&2; exit 1; }

# ------------------------------------------------------------------
# Environment check
# ------------------------------------------------------------------
check_env() {
    log "Checking environment…"

    if [ ! -f "$SHELL_BIN" ]; then
        die "Rust shell not built. Run: cd shell && cargo build --release"
    fi

    if [ -z "$OPENROUTER_API_KEY" ]; then
        warn "OPENROUTER_API_KEY not set. AI responses will fail without it."
        warn "Set it with: export OPENROUTER_API_KEY=sk_or_…"
    fi

    log "Environment OK"
}

# ------------------------------------------------------------------
# Cleanup old instances
# ------------------------------------------------------------------
cleanup() {
    log "Cleaning up old processes and sockets…"
    pkill -f "socket_server" 2>/dev/null || true
    rm -f "$SOCKET_PATH"
    sleep 1
}

# ------------------------------------------------------------------
# Start Python kernel server
# ------------------------------------------------------------------
start_kernel() {
    log "Starting Python kernel server on $SOCKET_PATH (TCP $TCP_PORT)…"

    # Ensure project root on PYTHONPATH so imports work
    export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"

    nohup python -m $PYTHON_KERNEL > "$KERNEL_LOG" 2>&1 &
    KERNEL_PID=$!

    log "Kernel server PID: $KERNEL_PID"

    # Wait for Unix socket to appear
    local waited=0
    while [ ! -S "$SOCKET_PATH" ]; then
        sleep 0.5
        waited=$((waited + 1))
        if [ $waited -ge $((MAX_WAIT_SECONDS * 2)) ]; then
            kill $KERNEL_PID 2>/dev/null || true
            die "Kernel server did not create socket within ${MAX_WAIT_SECONDS}s"
        fi
    done

    log "Unix socket ready (waited ${waited}s)"

    # Verify server is alive — send ping
    waited=0
    while ! echo '{"cmd":"ping"}' | socat -T 1 - UNIX-CONNECT:"$SOCKET_PATH" > /dev/null 2>&1; do
        sleep 0.5
        waited=$((waited + 1))
        if [ $waited -ge $((MAX_WAIT_SECONDS * 2)) ]; then
            kill $KERNEL_PID 2>/dev/null || true
            die "Kernel server not responding to ping within ${MAX_WAIT_SECONDS}s"
        fi
    done

    log "Kernel server is healthy (PID $KERNEL_PID)"
}

# ------------------------------------------------------------------
# Start Rust shell
# ------------------------------------------------------------------
start_shell() {
    log "Launching Bantu-OS shell…"
    cd "$KERNEL_DIR"
    exec "$SHELL_BIN"
}

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
main() {
    echo ""
    log "=== Bantu-OS Boot ==="
    echo ""
    log "Socket : $SOCKET_PATH"
    log "TCP    : 127.0.0.1:$TCP_PORT"
    log "Shell  : $SHELL_BIN"
    echo ""

    check_env
    cleanup
    start_kernel
    start_shell
}

main "$@"
