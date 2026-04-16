#!/bin/bash
# Build initramfs for Bantu-OS
# Creates a cpio.gz archive containing the C init daemon and minimal tooling.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
OVERLAY_DIR="$SCRIPT_DIR/overlay"
OUTPUT="$SCRIPT_DIR/initramfs.cpio.gz"

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "=== Bantu-OS Initramfs Builder ==="

# Copy overlay to staging
echo "Copying overlay..."
cp -a "$OVERLAY_DIR"/. "$BUILD_DIR/"

# Create required directories
mkdir -p "$BUILD_DIR/run/bantu"
mkdir -p "$BUILD_DIR/proc"
mkdir -p "$BUILD_DIR/sys"
mkdir -p "$BUILD_DIR/dev"

# Ensure the init binary exists and is executable
if [ ! -x "$BUILD_DIR/init" ]; then
    echo "WARNING: $BUILD_DIR/init is not executable or not found."
    echo "Place your compiled C init binary at initramfs/overlay/init"
fi

# If a custom init is provided via INITRAMFS_INIT env var, copy it over
if [ -n "$INITRAMFS_INIT" ] && [ -f "$INITRAMFS_INIT" ]; then
    echo "Using custom init: $INITRAMFS_INIT"
    cp "$INITRAMFS_INIT" "$BUILD_DIR/init"
    chmod +x "$BUILD_DIR/init"
fi

# Pack into cpio.gz
echo "Creating cpio archive..."
cd "$BUILD_DIR"
find . -print0 | cpio --quiet -0 -R 0:0 -H newc -o | gzip -9 > "$OUTPUT"

echo "=== Done ==="
echo "Output: $OUTPUT"
echo "Size:  $(du -h "$OUTPUT" | cut -f1)"
echo ""
echo "Usage: Pass to kernel via bootloader, e.g.:"
echo "  qemu-system-x86_64 -kernel /boot/vmlinuz -initrd initramfs.cpio.gz"
echo "  or add to GRUB: initrd /boot/initramfs-bantu.gz"