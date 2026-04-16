#ifndef BANTU_IPC_H
#define BANTU_IPC_H

#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>

#define IPC_MAGIC       0x42414E54  // "BANT" in LE
#define IPC_MAX_PAYLOAD 4096
#define IPC_MAX_QUEUE   64

typedef enum {
    IPC_MSG_REQUEST  = 0x01,
    IPC_MSG_RESPONSE = 0x02,
    IPC_MSG_NOTIFY   = 0x03,
    IPC_MSG_SIGNAL   = 0x04,
} ipc_msg_type_t;

typedef enum {
    IPC_PRIO_LOW    = 0,
    IPC_PRIO_NORMAL = 1,
    IPC_PRIO_HIGH   = 2,
    IPC_PRIO_KERNEL = 3,
} ipc_priority_t;

typedef struct {
    uint32_t magic;
    uint8_t  type;
    uint8_t  priority;
    uint16_t payload_len;
    int32_t  sender_pid;
    int32_t  receiver_pid;
    int32_t  reply_to;
    uint8_t  data[IPC_MAX_PAYLOAD];
} ipc_message_t;

typedef struct _ipc_channel {
    int32_t             pid;
    int                 read_fd;
    int                 write_fd;
    struct _ipc_channel* next;
} ipc_channel_t;

typedef struct {
    ipc_channel_t* channels;
    int             count;
} ipc_endpoint_t;

int  ipc_endpoint_create(int32_t pid, ipc_endpoint_t* ep);
void ipc_endpoint_destroy(ipc_endpoint_t* ep);
int  ipc_send(ipc_endpoint_t* from, int32_t to_pid, ipc_message_t* msg);
int  ipc_recv(ipc_endpoint_t* ep, ipc_message_t* msg, uint32_t timeout_ms);
int  ipc_reply(ipc_endpoint_t* ep, ipc_message_t* original, void* payload, size_t len);
void ipc_set_priority(ipc_message_t* msg, ipc_priority_t prio);

#endif