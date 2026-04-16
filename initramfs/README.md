# Bantu-OS Initramfs

Minimal initial ramdisk for Bantu-OS boot process.

## Structure

```
overlay/
├── init            # C init binary (PID 1 in initramfs)
├── bin/            # Minimal binaries (busybox symlinks, etc.)
├── lib/            # Shared libraries needed by init
├── run/
│   └── bantu/
│       └── init.sock  # Unix socket for Python service IPC
├── proc/           # procfs mount point
├── sys/            # sysfs mount point
└── dev/            # devtmpfs mount point
```

## Build

```bash
./build.sh
```

Output: `initramfs.cpio.gz`

## Usage

### QEMU

```bash
qemu-system-x86_64 \
    -kernel /boot/vmlinuz \
    -initrd initramfs.cpio.gz \
    -append "console=ttyS0"
```

### GRUB

```grub
menuentry 'Bantu-OS' {
    linux /boot/vmlinuz
    initrd /boot/initramfs-bantu.gz
}
```

## Custom Init Binary

Set `INITRAMFS_INIT` environment variable to replace the default `overlay/init`:

```bash
INITRAMFS_INIT=/path/to/my/init ./build.sh
```

## Boot Flow

1. Kernel mounts initramfs, executes `/init`
2. C init sets up `/proc`, `/sys`, `/dev`, creates socket at `/run/bantu/init.sock`
3. C init forks and execs Python runtime
4. Python services register via socket
5. C init enters event loop monitoring child processes and IPC