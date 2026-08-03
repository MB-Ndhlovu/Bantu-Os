#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>
#include "registry_socket.h"
#include "services.h"

static int write_response(int fd, const char *json)
{
    size_t len = strlen(json);
    const char *cursor = json;

    while (len > 0) {
        ssize_t written = write(fd, cursor, len);
        if (written < 0) {
            if (errno == EINTR)
                continue;
            return -1;
        }
        if (written == 0)
            return -1;
        cursor += written;
        len -= (size_t)written;
    }
    return 0;
}

static void handle_request(int fd)
{
    char request[512] = {0};
    ssize_t n = read(fd, request, sizeof(request) - 1);
    if (n <= 0)
        return;

    char cmd[32] = {0};
    char name[MAX_SERVICE_NAME] = {0};
    int pid = 0;
    int has_pid = 0;
    int parsed = sscanf(request, "{\"cmd\": \"%31[^\"]\", \"name\": \"%63[^\"]\", \"pid\": %d}", cmd, name, &pid);
    if (parsed < 2)
        parsed = sscanf(request, "{\"cmd\":\"%31[^\"]\",\"name\":\"%63[^\"]\",\"pid\":%d}", cmd, name, &pid);
    has_pid = strstr(request, "\"pid\"") != NULL;

    if (strcmp(cmd, "register") == 0 && parsed >= 2) {
        service_t *svc = service_find(name);
        if (!svc) {
            service_t external = {0};
            strncpy(external.name, name, MAX_SERVICE_NAME - 1);
            strncpy(external.exec_path, "/external", MAX_SERVICE_PATH - 1);
            external.priority = PRIORITY_USER;
            external.restart_policy = RESTART_NONE;
            if (service_register(&external) != 0) {
                write_response(fd, "{\"ok\":false,\"message\":\"registration failed\"}\n");
                return;
            }
        }
        service_set_external_state(name, has_pid ? (pid_t)pid : -1, SERVICE_RUNNING);
        write_response(fd, "{\"ok\":true,\"message\":\"registered\"}\n");
    } else if (strcmp(cmd, "heartbeat") == 0 && parsed >= 2) {
        if (!service_find(name)) {
            write_response(fd, "{\"ok\":false,\"message\":\"not registered\"}\n");
            return;
        }
        service_set_external_state(name, has_pid ? (pid_t)pid : -1, SERVICE_RUNNING);
        write_response(fd, "{\"ok\":true,\"message\":\"heartbeat\"}\n");
    } else if (strcmp(cmd, "unregister") == 0 && parsed >= 2) {
        service_set_external_state(name, -1, SERVICE_STOPPED);
        write_response(fd, "{\"ok\":true,\"message\":\"unregistered\"}\n");
    } else if (strcmp(cmd, "status") == 0 && parsed >= 2) {
        service_t *svc = service_find(name);
        if (svc) {
            char response[256];
            snprintf(response, sizeof(response), "{\"ok\":true,\"name\":\"%s\",\"pid\":%d,\"state\":\"%s\"}\n", svc->name, (int)svc->pid, service_state_str(svc->state));
            write_response(fd, response);
        } else {
            write_response(fd, "{\"ok\":false,\"message\":\"not found\"}\n");
        }
    } else {
        write_response(fd, "{\"ok\":false,\"message\":\"invalid request\"}\n");
    }
}

int registry_socket_start(const char *path)
{
    if (!path || path[0] == '\0' || strlen(path) >= sizeof(((struct sockaddr_un *)0)->sun_path)) {
        errno = EINVAL;
        return -1;
    }

    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0)
        return -1;
    unlink(path);
    struct sockaddr_un address = {0};
    address.sun_family = AF_UNIX;
    strncpy(address.sun_path, path, sizeof(address.sun_path) - 1);
    if (bind(fd, (struct sockaddr *)&address, sizeof(address)) < 0 || listen(fd, 8) < 0 || chmod(path, 0660) < 0) {
        close(fd);
        unlink(path);
        return -1;
    }
    return fd;
}

int registry_socket_poll(int server_fd, int timeout_ms)
{
    if (server_fd < 0 || timeout_ms < 0) {
        errno = EINVAL;
        return -1;
    }

    fd_set readfds;
    struct timeval timeout = {.tv_sec = timeout_ms / 1000, .tv_usec = (timeout_ms % 1000) * 1000};
    FD_ZERO(&readfds);
    FD_SET(server_fd, &readfds);
    int ready = select(server_fd + 1, &readfds, NULL, NULL, &timeout);
    if (ready < 0)
        return -1;
    if (ready > 0 && FD_ISSET(server_fd, &readfds)) {
        int client = accept(server_fd, NULL, NULL);
        if (client >= 0) {
            handle_request(client);
            close(client);
        }
    }
    return ready;
}

void registry_socket_close(int server_fd, const char *path)
{
    if (server_fd >= 0)
        close(server_fd);
    unlink(path);
}
