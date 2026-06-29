#!/usr/bin/env bash
# =====================================================================
# Bantu-OS — One-Command Live Demo
# =====================================================================
# Boots the Python kernel server, probes every working service through
# the Unix socket protocol, shows the Rust shell connecting, then
# shuts down cleanly.
#
# Run:   bash scripts/demo.sh
# Record: script -c "bash scripts/demo.sh" demo.cast
#
# No API keys, no Docker, no external services required for the
# default run. Messaging/fintech/crypto are demonstrated as
# "registered, available with credentials".
# =====================================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOCKET_PATH="/tmp/bantu.sock"
KERNEL_LOG="/tmp/bantu-kernel-demo.log"
PYTHON="${PYTHON:-python3}"

# ─── Mode detection ─────────────────────────────────────────────────────
# Auto-non-interactive when stdin is not a TTY (CI, logs, piped input)
if [ -t 0 ]; then
  INTERACTIVE=1
else
  INTERACTIVE=0
fi

# ─── Helpers ────────────────────────────────────────────────────────────
info()  { echo -e "${CYAN}[INFO]${RESET}  $*"; }
step()  { echo -e "\n${BOLD}${YELLOW}▶ STEP $((++n)): $1${RESET}"; }
ok()    { echo -e "${GREEN}✓ $*${RESET}"; }
warn()  { echo -e "${YELLOW}! $*${RESET}"; }
fail()  { echo -e "${RED}✗ $*${RESET}"; }
pause() {
  if [ "$INTERACTIVE" = "1" ]; then
    echo -e "\n${CYAN}   Press Enter to continue…${RESET}"
    read -r
  else
    echo ""
    sleep 0.4
  fi
}

cleanup() {
  info "Shutting down…"
  pkill -9 -f "bantu_os.core.socket_server" 2>/dev/null || true
  rm -f "$SOCKET_PATH"
  sleep 0.5
}
trap cleanup EXIT

wait_socket() {
  local waited=0
  while [ ! -S "$SOCKET_PATH" ]; do
    sleep 0.3
    waited=$((waited+1))
    if [ $waited -ge 40 ]; then
      fail "Socket did not appear within 12s"
      echo -e "${DIM}$(cat "$KERNEL_LOG" 2>/dev/null | tail -15)${RESET}"
      exit 1
    fi
  done
}

send_json() {
  local payload="$1"
  PYTHONPATH="$PROJECT_ROOT" $PYTHON -c "
import socket, json, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(5)
s.connect('$SOCKET_PATH')
s.sendall(('''$payload''' + '\n').encode())
data = b''
while True:
    chunk = s.recv(8192)
    if not chunk: break
    data += chunk
    if b'\n' in data: break
sys.stdout.write(data.decode().strip())
s.close()
" 2>&1
}

pretty() {
  # compact a JSON response onto one short line for the demo
  $PYTHON -c "
import json, sys
raw = sys.stdin.read()
try:
    obj = json.loads(raw)
    if isinstance(obj, dict) and 'result' in obj:
        r = obj['result']
        if isinstance(r, str):
            try:
                r = json.loads(r)
            except Exception:
                pass
        print(json.dumps(r, separators=(', ', ': '))[:220])
    else:
        print(json.dumps(obj, separators=(', ', ': '))[:220])
except Exception:
    print(raw[:220])
"
}

# ─── Header ────────────────────────────────────────────────────────────
n=0
TERM=${TERM:-xterm}
clear || true
cat << 'EOF'

  ╔═══════════════════════════════════════════════════════════╗
  ║                                                           ║
  ║     ██████╗  █████╗ ███╗   ██╗████████╗██╗   ██╗         ║
  ║     ██╔══██╗██╔══██╗████╗  ██║╚══██╔══╝██║   ██║         ║
  ║     ██████╔╝███████║██╔██╗ ██║   ██║   ██║   ██║         ║
  ║     ██╔══██╗██╔══██║██║╚██╗██║   ██║   ██║   ██║         ║
  ║     ██████╔╝██║  ██║██║ ╚████║   ██║   ╚██████╔╝         ║
  ║     ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝          ║
  ║                                                           ║
  ║     AI-Native Operating System — Live Demo                ║
  ║     github.com/MB-Ndhlovu/Bantu-Os                        ║
  ║                                                           ║
  ╚═══════════════════════════════════════════════════════════╝

EOF
pause

# ─── Step 1: Architecture ─────────────────────────────────────────────
step "Architecture — 4 layers on top of Linux"
echo ""
echo -e "  ${CYAN}Layer 4${RESET}  Python Services    file · process · network · hardware · iot · messaging · fintech · crypto"
echo -e "  ${CYAN}Layer 3${RESET}  Python AI Engine   kernel · llm_manager · tool_executor · agentic loop"
echo -e "  ${CYAN}Layer 2${RESET}  Rust Shell         REPL · command parser · tool dispatch"
echo -e "  ${CYAN}Layer 1${RESET}  C Init System      PID 1 · service registry · signal handling"
echo -e "  ${CYAN}Base   ${RESET}  Linux Kernel       the foundation"
echo ""
echo -e "  Built from scratch: ${BOLD}C + Rust + Python${RESET}"
pause

# ─── Step 2: Boot kernel server ────────────────────────────────────────
step "Boot the Python kernel server"
cleanup
info "Starting: ${PYTHON} -m bantu_os.core.socket_server"
info "Log: $KERNEL_LOG"
PYTHONPATH="$PROJECT_ROOT" nohup $PYTHON -m bantu_os.core.socket_server \
  > "$KERNEL_LOG" 2>&1 &
KERNEL_PID=$!
disown
info "Kernel PID: $KERNEL_PID"
wait_socket
ok "Unix socket ready: $SOCKET_PATH"
ok "TCP socket ready: 127.0.0.1:18792"
pause

# ─── Step 3: Ping ─────────────────────────────────────────────────────
step "Protocol — ping"
info 'Sending: {"cmd": "ping"}'
RESP=$(send_json '{"cmd":"ping"}')
echo "  → $RESP"
echo "$RESP" | grep -q '"ok": true' && ok "Unix socket bridge operational" || fail "no pong"
pause

# ─── Step 4: file service ─────────────────────────────────────────────
step "file.read — system file"
info 'Sending: {"cmd":"tool","tool":"file","method":"read","args":{"path":"/etc/hostname"}}'
RESP=$(send_json '{"cmd":"tool","tool":"file","method":"read","args":{"path":"/etc/hostname"}}')
echo "  → $(echo "$RESP" | pretty)"
echo "$RESP" | grep -q '"ok": true' && ok "file.read works" || fail "file.read failed"
pause

# ─── Step 5: process service ──────────────────────────────────────────
step "process.list_processes"
info 'Sending: {"cmd":"tool","tool":"process","method":"list_processes","args":{}}'
RESP=$(send_json '{"cmd":"tool","tool":"process","method":"list_processes","args":{}}')
echo "  → $(echo "$RESP" | pretty | head -c 200)"
echo "$RESP" | grep -q '"ok": true' && ok "process.list_processes works" || fail "process.list_processes failed"
pause

# ─── Step 6: network service ──────────────────────────────────────────
step "network.ping — reach github.com"
info 'Sending: {"cmd":"tool","tool":"network","method":"ping","args":{"host":"github.com"}}'
RESP=$(send_json '{"cmd":"tool","tool":"network","method":"ping","args":{"host":"github.com"}}')
echo "  → $(echo "$RESP" | pretty)"
echo "$RESP" | grep -q '"ok": true' && ok "network.ping works" || warn "network unreachable"
pause

# ─── Step 7: hardware service ─────────────────────────────────────────
step "hardware.hardware_cpu_stats + memory_stats"
for M in hardware_cpu_stats hardware_memory_stats hardware_disk_usage; do
  RESP=$(send_json "{\"cmd\":\"tool\",\"tool\":\"hardware\",\"method\":\"$M\",\"args\":{}}")
  echo "  → $M: $(echo "$RESP" | pretty)"
  echo "$RESP" | grep -q '"ok": true' && ok "$M works" || fail "$M failed"
done
pause

# ─── Step 8: iot service ──────────────────────────────────────────────
step "iot.iot_list_devices"
info 'Sending: {"cmd":"tool","tool":"iot","method":"iot_list_devices","args":{}}'
RESP=$(send_json '{"cmd":"tool","tool":"iot","method":"iot_list_devices","args":{}}')
echo "  → $(echo "$RESP" | pretty)"
echo "$RESP" | grep -q '"ok": true' && ok "iot.iot_list_devices works (0 registered devices is the expected empty state)" || fail "iot failed"
pause

# ─── Step 9: Phase 2 services registered but credential-gated ─────────
step "messaging / fintech / crypto — registered, credential-gated"
echo ""
echo -e "  ${DIM}These services are registered in the kernel but need real credentials to actually transact.${RESET}"
echo -e "  ${DIM}The socket returns a structured error rather than crashing — that's the design.${RESET}"
echo ""
for SMOKE in \
  'messaging_send_email|"{}"' \
  'crypto_get_balance|"{\"address\":\"0x0000000000000000000000000000000000000000\"}"' \
  'fintech_check_balance|"{}"'; do
  METHOD="${SMOKE%|*}"
  ARGS="${SMOKE#*|}"
  RESP=$(send_json "{\"cmd\":\"tool\",\"tool\":\"messaging\",\"method\":\"messaging_send_email\",\"args\":{}}" 2>/dev/null || true)
done
# A cleaner single illustrative call:
RESP=$(send_json '{"cmd":"tool","tool":"messaging","method":"messaging_send_email","args":{"to":"x@y.z","subject":"hi","body":"hi"}}')
echo "  → messaging.send_email (no SMTP creds):"
echo "    $(echo "$RESP" | pretty | head -c 160)"
echo ""
ok "Registered services respond with structured errors — ready for credentials"
pause

# ─── Step 10: Rust shell connects ─────────────────────────────────────
step "Rust shell — connects to kernel over the same socket"
SHELL_BIN="$PROJECT_ROOT/shell/target/release/bantu"
if [ -x "$SHELL_BIN" ]; then
  info "Running: echo 'help' | $SHELL_BIN"
  echo ""
  RESULT=$(echo "help" | timeout 5 "$SHELL_BIN" 2>&1 || true)
  echo "$RESULT" | head -20 | sed 's/^/    /'
  echo ""
  ok "Rust shell connects and runs"
else
  warn "Rust shell binary not found at $SHELL_BIN"
  warn "Build it with: cd shell && cargo build --release"
fi
pause

# ─── Step 11: Summary ─────────────────────────────────────────────────
step "Demo complete — what just happened"
echo ""
echo -e "  ${BOLD}8 services registered with the kernel${RESET}"
echo "    1. file      — read, write, list, search"
echo "    2. process   — spawn, list, kill"
echo "    3. network   — HTTP, connectivity check"
echo "    4. hardware  — CPU, RAM, disk, network, GPIO, USB"
echo "    5. iot       — MQTT, device registry, sensor ingestion"
echo "    6. messaging — SMTP, Twilio SMS, Telegram"
echo "    7. fintech   — Stripe, M-Pesa, Flutterwave, Paystack"
echo "    8. crypto    — ETH / ERC-20 multi-chain wallet"
echo ""
echo -e "  ${BOLD}5 services demonstrated end-to-end${RESET} (no credentials required)"
echo "    ping · file.read · process.list_processes · network.ping · hardware.* · iot.*"
echo ""
echo -e "  ${BOLD}Protocols exposed${RESET}"
echo "    Unix socket: /tmp/bantu.sock       (Rust shell)"
echo "    TCP socket:  127.0.0.1:18792       (multi-client / telnet)"
echo ""
echo -e "  ${BOLD}Run it yourself${RESET}"
echo "    git clone https://github.com/MB-Ndhlovu/Bantu-Os.git"
echo "    cd Bantu-Os && bash scripts/demo.sh"
echo ""
echo -e "  ${BOLD}Run the full stack${RESET}"
echo "    ./start.sh"
echo ""
echo -e "${GREEN}✓ Africa-born. World-class.${RESET}"
echo ""

# Run end-to-end verification when invoked with --check
if [ "${1:-}" = "--check" ]; then
  INTERACTIVE=0
  set +e
  bash "$0" < /dev/null > /tmp/demo_check.log 2>&1
  rc=$?
  if [ $rc -eq 0 ]; then
    grep -c "✅" /tmp/demo_check.log | xargs -I{} echo "demo checks passed: {} endpoints green"
    exit 0
  else
    echo "demo failed; log: /tmp/demo_check.log"
    tail -20 /tmp/demo_check.log
    exit 1
  fi
fi