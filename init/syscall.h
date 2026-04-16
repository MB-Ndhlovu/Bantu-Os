#ifndef BANTU_SYSCALL_H
#define BANTU_SYSCALL_H

#include <stdint.h>

#define SYSCALL_MAX 128

typedef int64_t (*syscall_handler_t)(int arg1, int arg2, int arg3, int arg4);

typedef struct {
    uint8_t num;
    const char* name;
    syscall_handler_t handler;
    uint8_t flags;
} syscall_entry_t;

#define SYSCALL_F_READ  0x01
#define SYSCALL_F_WRITE 0x02
#define SYSCALL_F_EXEC  0x04

void syscall_register(uint8_t num, const char* name, syscall_handler_t handler, uint8_t flags);
int64_t syscall_dispatch(uint8_t num, int arg1, int arg2, int arg3, int arg4);
void syscall_table_init(void);
const char* syscall_name(uint8_t num);
int syscall_validate(uint8_t num, uint8_t required_flags);

#endif