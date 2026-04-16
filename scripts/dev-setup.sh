#!/bin/bash
set -e

echo "==> Bantu-OS Dev Setup"

# Detect distro
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
else
    DISTRO="unknown"
fi

echo "[*] Distro detected: $DISTRO"

# Install system deps
install_deps() {
    case "$DISTRO" in
        ubuntu|debian)
            sudo apt-get update
            sudo apt-get install -y python3 python3-dev python3-venv git gcc make curl
            ;;
        fedora|rhel)
            sudo dnf install -y python3 python3-devel git gcc make curl
            ;;
        arch)
            sudo pacman -S --noconfirm python python-pip git gcc make curl
            ;;
        *)
            echo "[!] Unsupported distro. Install python3, git, gcc, make manually."
            ;;
    esac
}

install_deps

# Install Poetry
if ! command -v poetry &> /dev/null; then
    echo "[*] Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Create venv
if [ ! -d ".venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install deps
echo "[*] Installing Python dependencies..."
poetry install --with dev

# Verify install
echo ""
echo "==> Setup complete"
echo "Activate the environment with: source .venv/bin/activate"
echo "Run tests with: make test"
echo "Run shell with: poetry run bantu"