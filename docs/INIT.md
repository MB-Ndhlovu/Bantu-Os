# Bantu-OS Init System Design

## Overview

The Bantu-OS init system is a from-scratch replacement for systemd, written in C. It runs as PID 1 after the Linux kernel boots and is responsible for initializing the system.

## What It Does

### Boot Sequence

1. **PID 1 Startup**
   - Becomes the first userspace process
   - Sets up signal handlers for child process management

2. **Filesystem Mounting**
   - `/proc` - Process information pseudo-filesystem
   - `/sys` - System ABI pseudo-filesystem
   - `/run` - Volatile runtime files (tmpfs)
   - `/dev/pts` - Pseudo-terminal master

3. **Device Setup**
   - Creates essential device nodes: `/dev/null`, `/dev/zero`, `/dev/console`

4. **Service Initialization**
   - Loads services from `/etc/bantu/services.conf` (or uses defaults)
   - Starts services in priority order

5. **AI Engine Start**
   - Launches the Python-based AI engine (`main.py`)

6. **Shell/UI Start**
   - Launches the AI shell (Rust-based) or falls back to `/bin/sh`

### Shutdown Sequence

1. Stop all services in reverse priority order
2. Sync filesystems
3. Call `reboot()` to power off

## Services

### Startup Order (Priority)

| Priority | Services |
|----------|----------|
| CRITICAL (0) | Filesystem mounting (internal) |
| EARLY (10) | syslog, early logging |
| NORMAL (50) | network, other system services |
| LATE (100) | User services, GUI |
| USER (200) | User-specific startup |

### Default Services

```
syslog:10:/sbin/syslogd
network:50:/etc/bantu/network.sh
```

## Service Definition

Services are defined using a `struct service` with callback functions:

```c
typedef struct service {
    char name[64];                    // Service name
    char exec_path[256];              // Path to executable
    char **argv;                      // Argument vector
    char **env;                       // Environment variables
    
    service_priority_t priority;      // Start priority (0-200)
    service_state_t state;            // Current state
    uint32_t restart_policy;          // Auto-restart settings
    uint32_t max_restarts;            // Max restart attempts
    
    pid_t pid;                        // Process ID when running
    
    // Callbacks
    service_start_fn on_start;        // Pre-start callback
    service_stop_fn on_stop;          // Pre-stop callback
    service_restart_fn on_restart;    // Pre-restart callback
    
    struct service *next;             // Next service in list
} service_t;
```

### States

- `SERVICE_STOPPED` - Not running
- `SERVICE_STARTING` - In the process of starting
- `SERVICE_RUNNING` - Active and running
- `SERVICE_STOPPING` - In the process of stopping
- `SERVICE_FAILED` - Failed to start

### Callbacks

Services can register three optional callbacks:

```c
typedef int (*service_start_fn)(void);
typedef int (*service_stop_fn)(void);
typedef int (*service_restart_fn)(void);
```

Example usage:

```c
int my_service_on_start(void) {
    printf("Preparing service...");
    return 0;  // Return 0 for success
}

service_t my_service = {
    .name = "my_service",
    .exec_path = "/usr/bin/my_service",
    .priority = PRIORITY_NORMAL,
    .on_start = my_service_on_start,
    .on_stop = NULL,
    .on_restart = NULL
};

service_register(&my_service);
```

## Configuration File Format

`/etc/bantu/services.conf`:

```
# Format: name:priority:path[:arg1:arg2:...]
syslog:10:/sbin/syslogd
network:50:/etc/bantu/network.sh:--background
userapps:100:/usr/bin/userappmgr
```

- Lines starting with `#` or `;` are comments
- Empty lines are ignored
- Fields separated by `:`

## API Reference

### Registry Functions

```c
void service_registry_init(void);           // Initialize empty registry
int service_register(service_t *svc);       // Add service to registry
int service_unregister(const char *name);   // Remove service by name
service_t *service_find(const char *name);  // Find service by name
void service_free_registry(void);           // Free all services
```

### Lifecycle Functions

```c
int start_service(service_t *svc);          // Start a single service
int stop_service(service_t *svc);           // Stop a single service
int restart_service(service_t *svc);        // Restart a service
void start_all_services(void);              // Start all registered services
void stop_all_services(void);               // Stop all services
```

### Configuration Functions

```c
int load_services_from_config(const char *path);  // Load from file
int parse_config_line(const char *line, service_t *svc);  // Parse single line
```

### Monitoring Functions

```c
int wait_for_service(service_t *svc, int timeout_ms);
bool is_service_running(const char *name);
int get_service_exit_code(const char *name);
```

### Utility Functions

```c
const char *service_state_str(service_state_t state);  // State to string
void dump_services(void);                    // Debug: print all services
```

## Future Enhancements

- [ ] Dependency resolution between services
- [ ] Service restart policies (on-failure, always, etc.)
- [ ] Socket activation (on-demand service start)
- [ ] Cgroups integration for resource control
- [ ] Health check callbacks
- [ ] D-Bus integration for inter-service communication
- [ ] Logging to `/var/log/bantu/` with rotation
- [ ] Configuration hot-reload (SIGHUP)
- [ ] Service namespaces (per-service filesystem, network, etc.)
- [ ] Init scripts compatibility layer

## Building

```bash
# Compile the init system
cd init
make

# Compile tests
make test

# Run tests
./tests/test_services
```

## Files

- `init/init.c` - Main init process (PID 1)
- `init/services.h` - Service registry header
- `init/services.c` - Service registry implementation
- `init/tests/test_services.c` - Unit tests
- `init/tests/Makefile` - Test build file
- `docs/INIT.md` - This documentation
