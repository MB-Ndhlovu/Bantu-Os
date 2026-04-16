#include "errors.h"
#include <string.h>

static const struct {
    int code;
    const char* msg;
} error_table[] = {
    { BANTU_OK,              "success" },
    { BANTU_ERR_INVALID,    "invalid argument" },
    { BANTU_ERR_NULL_PTR,   "null pointer" },
    { BANTU_ERR_NO_MEM,     "out of memory" },
    { BANTU_ERR_NOT_FOUND,  "not found" },
    { BANTU_ERR_TIMEOUT,    "operation timed out" },
    { BANTU_ERR_PERMISSION, "permission denied" },
    { BANTU_ERR_INVALID_SYSCALL,  "invalid syscall number" },
    { BANTU_ERR_NOT_IMPLEMENTED,   "not implemented" },
    { BANTU_ERR_IPC_FAILED,        "IPC operation failed" },
    { BANTU_ERR_BUFFER_FULL,      "buffer full" },
    { BANTU_ERR_QUEUE_EMPTY,      "queue empty" },
};

const char* bantu_strerror(int err) {
    for (int i = 0; i < (int)(sizeof(error_table)/sizeof(error_table[0])); i++) {
        if (error_table[i].code == err) {
            return error_table[i].msg;
        }
    }
    return "unknown error";
}