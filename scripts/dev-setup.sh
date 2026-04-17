#!/bin/bash
set -e
set -u

# ── Config ──────────────────────────────────────────────────────────────────
REPO_URL="${REPO_URL:-https://github.com/MB-Ndhlovu/Bantu-Os.git}"
CLONE_DIR="${CLONE_DIR:-/home/workspace/bantu_os}"
POETRY_URL="https://install.python-poetry.org"

# ── Helpers ─────────────────────────────────────────────────────────────────
info()  { echo "[*] $*"; }
warn()  { echo "[!] $*" >&2; }
fail()  { echo "[✗] $*" >&2; exit 1; }

is_cmd() { command -v "$1" >/dev/null 2>&1; }

# ── Detect distro ────────────────────────────────────────────────────────────
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif [ -f /etc/redhat-release ]; then
        echo "rhel"
    else
        echo "unknown"
    fi
}

# ── Install system deps ──────────────────────────────────────────────────────
install_system_deps() {
    info "Detected distro: $1"
    case "$1" in
        ubuntu|debian|linuxmint)
            sudo apt-get update
            sudo apt-get install -y python3 python3-dev python3-venv git gcc make curl clang-format
            ;;
        fedora|rhel|centos)
            sudo dnf install -y python3 python3-devel git gcc make curl clang-format
            ;;
        arch|manjaro)
            sudo pacman -S --noconfirm python python-pip git gcc make curl clang-format
            ;;
        alpine)
            apk add --no-cache python3 python3-dev git gcc musl-dev make curl clang
            ;;
        *)
            warn "Unsupported distro. Please install manually: python3, git, gcc, make, curl, clang-format"
            ;;
    esac
}

# ── Install Rust ─────────────────────────────────────────────────────────────
install_rust() {
    if is_cmd rustc; then
        info "Rust already installed: $(rustc --version)"
        return
    fi
    info "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    . "$HOME/.cargo/env"
    info "Rust installed: $(rustc --version)"
}

# ── Install Poetry ───────────────────────────────────────────────────────────
install_poetry() {
    if is_cmd poetry; then
        info "Poetry already installed: $(poetry --version)"
        return
    fi
    info "Installing Poetry..."
    curl -sSL "$POETRY_URL" | python3 -
    # Detect install location and add to PATH
    if [ -f "$HOME/.local/bin/poetry" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    elif [ -f "$HOME/.poetry/bin/poetry" ]; then
        export PATH="$HOME/.poetry/bin:$PATH"
    fi
    info "Poetry installed: $(poetry --version)"
}

# ── Clone / update repo ──────────────────────────────────────────────────────
setup_repo() {
    if [ -d "$CLONE_DIR/.git" ]; then
        info "Repo already exists at $CLONE_DIR – pulling latest main..."
        cd "$CLONE_DIR"
        git fetch origin main
        git checkout main
        git pull origin main
    else
        info "Cloning Bantu-OS to $CLONE_DIR..."
        git clone "$REPO_URL" "$CLONE_DIR"
        cd "$CLONE_DIR"
    fi
}

# ── Install Python deps ───────────────────────────────────────────────────────
install_python_deps() {
    info "Installing Python dependencies with Poetry..."
    poetry install --with dev --no-interaction
}

# ── Verify build ─────────────────────────────────────────────────────────────
verify_build() {
    info "Verifying builds..."

    # Python
    python3 -c "import bantu_os" && info "Python: OK" || { warn "Python import failed"; }

    # Rust
    if is_cmd cargo; do
        . "$HOME/.cargo/env" 2>/dev/null || true
        cd "$CLONE_DIR/shell"
        cargo check --message-format=short 2>&1 | tail -3
        cd "$CLONE_DIR"
    fi

    # C
    cd "$CLONE_DIR/init"
    make clean >/dev/null 2>&1
    if make >/dev/null 2>&1; then
        info "C (init): OK"
    else
        warn "C (init) build had warnings or errors – check manually"
    fi
    cd "$CLONE_DIR"
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
    DISTRO=$(detect_distro)
    info "Bantu-OS Development Setup"
    info "Installing for distro: $DISTRO"

    install_system_deps "$DISTRO"
    install_rust
    install_poetry

    # Ensure poetry in PATH for subsequent commands
    export PATH="$HOME/.local/bin:$PATH"

    setup_repo
    install_python_deps

    # Reload shell to pick up Poetry PATH
    info "Installing Rust toolchain for shell..."
    . "$HOME/.cargo/env" 2>/dev/null || true
    cd "$CLONE_DIR/shell"
    if command -v cargo >/dev/null 2>&1; then
        cargo fetch 2>&1 | tail -2 || true
    fi
    cd "$CLONE_DIR"

    verify_build

    echo ""
    info "Setup complete!"
    echo "  Activate Poetry env: cd $CLONE_DIR && poetry shell"
    echo "  Run tests:           cd $CLONE_DIR && make test"
    echo "  Format code:         cd $CLONE_DIR && make format"
    echo "  Build Docker:        cd $CLONE_DIR && make docker-build"
}

main "$@"