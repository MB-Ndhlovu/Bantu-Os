#!/bin/bash
# Build the Linux kernel for Bantu-OS
# Usage: ./build.sh [KERNEL_SOURCE_DIR]
#
# What this script does:
# 1. Accepts an optional KERNEL_SOURCE_DIR (defaults to /usr/src/linux or current dir)
# 2. Copies kernel/config → KERNEL_SOURCE_DIR/.config
# 3. Runs make olddefconfig to reconcile any missing options with defaults
# 4. Runs make -j$(nproc) to compile the kernel
# 5. Runs make modules_install to install out-of-tree modules (if any)
# 6. Outputs: bzImage at KERNEL_SOURCE_DIR/arch/x86/boot/bzImage
#
# Prerequisites:
#   - GCC, binutils, make, flex, bison, libelf-dev, libssl-dev
#   - Linux kernel source (apt install linux-source or clone from kernel.org)
#
# Environment variables:
#   KERNEL_CONFIG  — override config file path (default: this script's directory/config)
#   MAKEFLAGS      — extra flags to make (e.g., V=1 for verbose)
#
# Note: This script does NOT install the kernel to /boot or update GRUB.
#   After a successful build, manually run:
#     cp arch/x86/boot/bzImage /boot/vmlinuz-bantu-X.Y.Z
#     update-grub  # or equivalent for your distro

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${KERNEL_CONFIG:-$SCRIPT_DIR/config}"
KERNEL_SOURCE="${1:-}"

# Determine kernel source directory
if [ -n "$KERNEL_SOURCE" ]; then
    if [ ! -d "$KERNEL_SOURCE" ]; then
        echo "ERROR: Kernel source directory not found: $KERNEL_SOURCE"
        exit 1
    fi
    echo "Using kernel source: $KERNEL_SOURCE"
else
    # Try to find kernel source
    for dir in /usr/src/linux /lib/modules/$(uname -r)/build /root/linux; do
        if [ -d "$dir" ] && [ -f "$dir/Makefile" ]; then
            KERNEL_SOURCE="$dir"
            break
        fi
    done

    if [ -z "$KERNEL_SOURCE" ]; then
        echo "ERROR: No kernel source found."
        echo "Usage: $0 /path/to/kernel/source"
        echo ""
        echo "Provide a kernel source directory as an argument, or ensure one of:"
        echo "  - /usr/src/linux"
        echo "  - /lib/modules/$(uname -r)/build"
        echo "  is available."
        exit 1
    fi
    echo "Using kernel source: $KERNEL_SOURCE"
fi

# Verify config file
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Kernel config not found at $CONFIG_FILE"
    exit 1
fi

echo "=== Bantu-OS Kernel Builder ==="
echo "Kernel source: $KERNEL_SOURCE"
echo "Config file:   $CONFIG_FILE"
echo "Output:        $KERNEL_SOURCE/arch/x86/boot/bzImage"
echo ""

# Change to kernel source
cd "$KERNEL_SOURCE"

# Backup existing .config if it exists
if [ -f .config ]; then
    echo "Backing up existing .config → .config.bak"
    cp .config .config.bak
fi

# Copy config
echo "Applying Bantu-OS kernel config..."
cp "$CONFIG_FILE" .config

# Make olddefconfig: resolve any new options not in config with defaults (non-interactive)
echo "Running make olddefconfig to reconcile config..."
make ARCH=x86_64 olddefconfig

# Build kernel
echo ""
echo "Building kernel (parallel jobs: $(nproc))..."
make ARCH=x86_64 CROSS_COMPILE= -j"$(nproc)" ${MAKEFLAGS:-}

# Verify bzImage exists
if [ ! -f arch/x86/boot/bzImage ]; then
    echo "ERROR: bzImage not found after build!"
    exit 1
fi

echo ""
echo "=== Build Complete ==="
echo "Kernel image: $KERNEL_SOURCE/arch/x86/boot/bzImage"
echo "Size:        $(du -h arch/x86/boot/bzImage | cut -f1)"
echo ""
echo "Next steps:"
echo "  cp arch/x86/boot/bzImage /boot/vmlinuz-bantu"
echo "  update-grub  # or manually add to GRUB config"