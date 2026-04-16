#define _POSIX_C_SOURCE 200809L
#include "ipc.h"
#include "../core/errors.h"
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/select.h>
#include <sys/time.h>
#include <stdio.h>

static int ipc_make_fifo(const char* path) {
    unlink(path);
    if (mkfifo(path, 0666) < 0) {
        return BANTU_ERR_IPC_FAILED;
    }
    return BANTU_OK;
}

static void ipc_path_for_pid(char* buf, size_t bufsiz, int32_t pid, int type) {
    snprintf(buf, bufsiz, "/tmp/bantu_ipc_%d_%c", pid, type == 0 ? 'r' : 'w');
}

int ipc_endpoint_create(int32_t pid, ipc_endpoint_t* ep) {
    if (!ep) return BANTU_ERR_NULL_PTR;

    char rpath[128], wpath[128];
    ipc_path_for_pid(rpath, sizeof(rpath), pid, 'r');
    ipc_path_for_pid(wpath, sizeof(wpath), pid, 'w');

    int ret;
    if ((ret = ipc_make_fifo(rpath)) != BANTU_OK) return ret;
    if ((ret = ipc_make_fifo(wpath)) != BANTU_OK) return ret;

    ipc_channel_t* ch = calloc(1, sizeof(ipc_channel_t));
    if (!ch) {
        unlink(rpath); unlink(wpath);
        return BANTU_ERR_NO_MEM;
    }

    ch->pid = pid;
    ch->read_fd = open(rpath, O_RDONLY | O_NONBLOCK);
    ch->write_fd = open(wpath, O_WRONLY);
    ch->next = NULL;

    ep->channels = ch;
    ep->count = 1;
    return BANTU_OK;
}

void ipc_endpoint_destroy(ipc_endpoint_t* ep) {
    if (!ep) return;
    ipc_channel_t* cur = ep->channels;
    while (cur) {
        if (cur->read_fd >= 0) close(cur->read_fd);
        if (cur->write_fd >= 0) close(cur->write_fd);
        ipc_channel_t* n = cur->next;
        free(cur);
        cur = n;
    }
    ep->channels = NULL;
    ep->count = 0;
}

int ipc_send(ipc_endpoint_t* from, int32_t to_pid, ipc_message_t* msg) {
    if (!from || !msg) return BANTU_ERR_NULL_PTR;
    if (msg->payload_len > IPC_MAX_PAYLOAD) return BANTU_ERR_INVALID;

    // Simple approach: write message to receiver's read fifo
    char rpath[128];
    ipc_path_for_pid(rpath, sizeof(rpath), to_pid, 'r');

    int fd = open(rpath, O_WRONLY | O_NONBLOCK);
    if (fd < 0) return BANTU_ERR_NOT_FOUND;

    // Encode as length-prefixed binary for safety
    uint32_t len = sizeof(ipc_message_t);
    write(fd, &len, sizeof(len));
    write(fd, msg, sizeof(ipc_message_t));
    close(fd);
    return BANTU_OK;
}

int ipc_recv(ipc_endpoint_t* ep, ipc_message_t* msg, uint32_t timeout_ms) {
    if (!ep || !msg) return BANTU_ERR_NULL_PTR;

    // Poll with timeout using select() — simplified
    fd_set rfds;
    struct timeval tv;
    FD_ZERO(&rfds);

    int maxfd = -1;
    ipc_channel_t* cur = ep->channels;
    while (cur) {
        if (cur->read_fd >= 0) {
            FD_SET(cur->read_fd, &rfds);
            if (cur->read_fd > maxfd) maxfd = cur->read_fd;
        }
        cur = cur->next;
    }

    if (maxfd < 0) return BANTU_ERR_NOT_FOUND;

    tv.tv_sec = timeout_ms / 1000;
    tv.tv_usec = (timeout_ms % 1000) * 1000;

    int ready = select(maxfd + 1, &rfds, NULL, NULL, &tv);
    if (ready <= 0) return BANTU_ERR_TIMEOUT;

    // Read from the ready fd
    cur = ep->channels;
    while (cur) {
        if (cur->read_fd >= 0 && FD_ISSET(cur->read_fd, &rfds)) {
            uint32_t len = 0;
            if (read(cur->read_fd, &len, sizeof(len)) != sizeof(len)) continue;
            if (len > sizeof(ipc_message_t)) continue;
            if (read(cur->read_fd, msg, len) == (ssize_t)len) {
                return BANTU_OK;
            }
        }
        cur = cur->next;
    }

    return BANTU_ERR_TIMEOUT;
}

int ipc_reply(ipc_endpoint_t* ep, ipc_message_t* original, void* payload, size_t len) {
    if (!original || !payload) return BANTU_ERR_NULL_PTR;
    if (len > IPC_MAX_PAYLOAD) return BANTU_ERR_INVALID;

    ipc_message_t reply = {
        .magic = IPC_MAGIC,
        .type  = IPC_MSG_RESPONSE,
        .payload_len = (uint16_t)len,
        .sender_pid  = original->receiver_pid,
        .receiver_pid = original->sender_pid,
        .reply_to = 0,  // not tracking original
    };
    memcpy(reply.data, payload, len);
    return ipc_send(ep, original->sender_pid, &reply);
}

void ipc_set_priority(ipc_message_t* msg, ipc_priority_t prio) {
    if (msg) msg->priority = (uint8_t)prio;
}