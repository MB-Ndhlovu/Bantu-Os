#!/bin/bash
# Bantu-OS Boot Launcher
# Starts Python kernel server first, then the Rust shell connects automatically.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
KERNEL_DIR="$PROJECT_ROOT"
SHELL_BIN="$PROJECT_ROOT/shell/target/release/bantu"
SOCKET_PATH="/tmp/bantu.sock"
PYTHON_KERNEL="bantu_os.core.socket_server"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[boot]${NC} $*"; }
warn() { echo -e "${YELLOW}[boot]${NC} WARNING: $*"; }
die() { echo -e "${RED}[boot]${NC} ERROR: $*" >&2; exit 1; }

# Check environment
check_env() {
    log "Checking environment..."

    if [ ! -f "$SHELL_BIN" ]; then
        die "Rust shell not built. Run: cd shell && cargo build --release"
    fi

    if [ -z "$OPENROUTER_API_KEY" ]; then
        warn "OPENROUTER_API_KEY not set. AI responses will fail."
        warn "Set it with: export OPENROUTER_API_KEY=your_key"
    fi

    log "Environment OK"
}

# Kill any existing instance
cleanup() {
    log "Cleaning up old processes..."
    pkill -f "socket_server" 2>/dev/null || true
    rm -f "$SOCKET_PATH"
    sleep 1
}

# Start Python kernel server
start_kernel() {
    log "Starting Python kernel server on $SOCKET_PATH..."

    cd "$KERNEL_DIR"
    nohup python -m $PYTHON_KERNEL > /tmp/bantu-kernel.log 2>&1 &
    KERNEL_PID=$!

    # Wait for socket to appear
    for i in $(seq 1 10); do
        if [ -S "$SOCKET_PATH" ]; then
            log "Kernel server ready (PID $KERNEL_PID)"
            return 0
        fi
        sleep 0.5
    done

    die "Kernel server failed to start. Check /tmp/bantu-kernel.log"
}

# Start Rust shell
start_shell() {
    log "Launching Bantu-OS shell..."
    cd "$KERNEL_DIR"
    exec "$SHELL_BIN"
}

# Main
main() {
    echo ""
    log "=== Bantu-OS Boot ==="
    echo ""

    check_env
    cleanup
    start_kernel
    start_shell
}

main "$@"
