#include "syscall.h"
#include "../core/errors.h"
#include <string.h>

static syscall_entry_t syscall_table[SYSCALL_MAX];
static uint8_t syscall_count = 0;

void syscall_table_init(void) {
    memset(syscall_table, 0, sizeof(syscall_table));
    syscall_count = 0;

    // Register core OS syscalls
    syscall_register(0, "exit",         NULL, SYSCALL_F_EXEC);
    syscall_register(1, "read",         NULL, SYSCALL_F_READ);
    syscall_register(2, "write",        NULL, SYSCALL_F_WRITE);
    syscall_register(3, "open",         NULL, SYSCALL_F_READ | SYSCALL_F_WRITE);
    syscall_register(4, "close",        NULL, 0);
    syscall_register(5, "fork",         NULL, SYSCALL_F_EXEC);
    syscall_register(6, "exec",         NULL, SYSCALL_F_EXEC);
    syscall_register(7, "wait",         NULL, SYSCALL_F_READ);
    syscall_register(8, "pipe",         NULL, 0);
    syscall_register(9, "kill",         NULL, SYSCALL_F_EXEC);
    syscall_register(10, "time",       NULL, SYSCALL_F_READ);
    // AI syscalls (64-95 reserved for AI subsystem)
    syscall_register(64, "ai_invoke",   NULL, SYSCALL_F_EXEC);
    syscall_register(65, "ai_memory",   NULL, SYSCALL_F_READ);
    syscall_register(66, "ai_tool",     NULL, SYSCALL_F_WRITE);
    // IPC syscalls (96-127)
    syscall_register(96, "ipc_send",    NULL, SYSCALL_F_WRITE);
    syscall_register(97, "ipc_recv",    NULL, SYSCALL_F_READ);
    syscall_register(98, "ipc_reply",   NULL, SYSCALL_F_WRITE);
}

void syscall_register(uint8_t num, const char* name, syscall_handler_t handler, uint8_t flags) {
    if (num >= SYSCALL_MAX) return;
    if (!name) return;

    // Only register once per slot
    for (int i = 0; i < SYSCALL_MAX; i++) {
        if (syscall_table[i].num == num) return;
    }

    syscall_table[syscall_count++] = (syscall_entry_t){
        .num = num,
        .name = name,
        .handler = handler,
        .flags = flags,
    };
}

int64_t syscall_dispatch(uint8_t num, int arg1, int arg2, int arg3, int arg4) {
    if (num >= SYSCALL_MAX) {
        return BANTU_ERR_INVALID_SYSCALL;
    }

    for (int i = 0; i < SYSCALL_MAX; i++) {
        if (syscall_table[i].num == num) {
            if (syscall_table[i].handler == NULL) {
                // No handler registered — this is a stub
                return BANTU_ERR_NOT_IMPLEMENTED;
            }
            return syscall_table[i].handler(arg1, arg2, arg3, arg4);
        }
    }

    return BANTU_ERR_INVALID_SYSCALL;
}

const char* syscall_name(uint8_t num) {
    for (int i = 0; i < SYSCALL_MAX; i++) {
        if (syscall_table[i].num == num) {
            return syscall_table[i].name;
        }
    }
    return "unknown";
}

int syscall_validate(uint8_t num, uint8_t required_flags) {
    for (int i = 0; i < SYSCALL_MAX; i++) {
        if (syscall_table[i].num == num) {
            return (syscall_table[i].flags & required_flags) == required_flags;
        }
    }
    return 0;
}