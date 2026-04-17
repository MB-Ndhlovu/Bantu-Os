#!/bin/bash
# Build the initramfs for Bantu-OS
#
# What this script does:
# 1. Copies boot/initramfs/overlay/ → staging directory
# 2. Ensures required mount points (/proc, /sys, /dev, /run) exist
# 3. Copies the compiled C init binary (init/init) to overlay/init
#    (or uses INITRAMFS_INIT env var if set)
# 4. Creates a cpio.gz archive ready for kernel boot
#
# Output: boot/initramfs.cpio.gz
#
# Usage:
#   ./build-initramfs.sh
#   INITRAMFS_INIT=/path/to/init ./build-initramfs.sh  # custom init binary

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OVERLAY_DIR="$SCRIPT_DIR/initramfs/overlay"
BUILD_DIR="$SCRIPT_DIR/build-initramfs"
OUTPUT="$SCRIPT_DIR/initramfs.cpio.gz"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== Bantu-OS Initramfs Builder ==="

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy overlay to staging
echo "Copying overlay..."
cp -a "$OVERLAY_DIR"/. "$BUILD_DIR/"

# Create required directories
echo "Creating mount points..."
mkdir -p "$BUILD_DIR/run/bantu"
mkdir -p "$BUILD_DIR/proc"
mkdir -p "$BUILD_DIR/sys"
mkdir -p "$BUILD_DIR/dev"

# Determine which init binary to use
INITBIN="$BUILD_DIR/init"

if [ -n "$INITRAMFS_INIT" ] && [ -f "$INITRAMFS_INIT" ]; then
    echo "Using custom init: $INITRAMFS_INIT"
    cp "$INITRAMFS_INIT" "$INITBIN"
    chmod +x "$INITBIN"
elif [ -f "$ROOT/init/init" ]; then
    echo "Using compiled C init: $ROOT/init/init"
    cp "$ROOT/init/init" "$INITBIN"
    chmod +x "$INITBIN"
else
    # Fall back to the shell stub in overlay (must be executable)
    if [ ! -x "$INITBIN" ]; then
        echo "WARNING: $INITBIN is not executable. Making it executable..."
        chmod +x "$INITBIN"
    fi
    echo "WARNING: No compiled init found — using shell stub. Build 'init' first."
fi

# Ensure the shell stub is also executable (in case we use it)
chmod +x "$BUILD_DIR/init" 2>/dev/null || true

# Pack into cpio.gz
echo "Creating cpio archive..."
cd "$BUILD_DIR"
find . -print0 | cpio --quiet -0 -R 0:0 -H newc -o | gzip -9 > "$OUTPUT"

echo ""
echo "=== Done ==="
echo "Output: $OUTPUT"
echo "Size:  $(du -h "$OUTPUT" | cut -f1)"
echo ""
echo "Usage:"
echo "  QEMU:  qemu-system-x86_64 -kernel /boot/vmlinuz -initrd $OUTPUT -append 'console=ttyS0'"
echo "  GRUB:  initrd /boot/initramfs-bantu.gz"
echo ""
echo "Next: Run 'make kernel' then 'make image' to assemble the full OS image."