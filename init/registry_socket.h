#ifndef BANTU_REGISTRY_SOCKET_H
#define BANTU_REGISTRY_SOCKET_H

int registry_socket_start(const char *path);
int registry_socket_poll(int server_fd, int timeout_ms);
void registry_socket_close(int server_fd, const char *path);

#endif
