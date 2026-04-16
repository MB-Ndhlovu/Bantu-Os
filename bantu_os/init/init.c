/*
 * bantu_os/init/init.c
 * Minimal Linux init system (PID 1) with service registry skeleton.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/wait.h>

#define MAX_SERVICES 64
#define MAX_NAME_LEN  64
#define MAX_PATH_LEN 256

typedef enum {
    SERVICE_STOPPED = 0,
    SERVICE_STARTING,
    SERVICE_RUNNING,
    SERVICE_STOPPING,
    SERVICE_FAILED
} ServiceState;

typedef struct Service {
    char name[MAX_NAME_LEN];
    char exec_path[MAX_PATH_LEN];
    pid_t pid;
    ServiceState state;
    int auto_restart;
} Service;

static Service service_registry[MAX_SERVICES];
static int registered_count = 0;

/*
 * Register a service in the registry.
 * Returns 0 on success, -1 on failure.
 */
int service_register(const char *name, const char *exec_path, int auto_restart)
{
    if (registered_count >= MAX_SERVICES) {
        fprintf(stderr, "[init] service registry full\n");
        return -1;
    }
    if (!name || !exec_path) {
        fprintf(stderr, "[init] invalid service arguments\n");
        return -1;
    }

    Service *svc = &service_registry[registered_count];
    memset(svc, 0, sizeof(Service));
    strncpy(svc->name, name, MAX_NAME_LEN - 1);
    strncpy(svc->exec_path, exec_path, MAX_PATH_LEN - 1);
    svc->pid = -1;
    svc->state = SERVICE_STOPPED;
    svc->auto_restart = auto_restart;

    registered_count++;
    printf("[init] registered service: %s -> %s\n", name, exec_path);
    return 0;
}

/*
 * Start a registered service by name.
 */
int service_start(const char *name)
{
    for (int i = 0; i < registered_count; i++) {
        if (strcmp(service_registry[i].name, name) == 0) {
            Service *svc = &service_registry[i];
            if (svc->state == SERVICE_RUNNING) {
                printf("[init] %s already running (pid %d)\n", name, svc->pid);
                return 0;
            }
            pid_t pid = fork();
            if (pid == 0) {
                execl(svc->exec_path, svc->exec_path, (char *)NULL);
                _exit(127);
            } else if (pid > 0) {
                svc->pid = pid;
                svc->state = SERVICE_RUNNING;
                printf("[init] started %s (pid %d)\n", name, pid);
                return 0;
            } else {
                perror("[init] fork failed");
                return -1;
            }
        }
    }
    fprintf(stderr, "[init] service not found: %s\n", name);
    return -1;
}

/*
 * Reap zombie child processes.
 */
void reap_children(void)
{
    int status;
    pid_t pid;
    while ((pid = waitpid(-1, &status, WNOHANG)) > 0) {
        for (int i = 0; i < registered_count; i++) {
            if (service_registry[i].pid == pid) {
                printf("[init] %s exited (status %d)\n",
                       service_registry[i].name, WEXITSTATUS(status));
                if (service_registry[i].auto_restart &&
                    service_registry[i].state == SERVICE_RUNNING) {
                    printf("[init] auto-restarting %s\n", service_registry[i].name);
                    service_start(service_registry[i].name);
                } else {
                    service_registry[i].state = SERVICE_STOPPED;
                    service_registry[i].pid = -1;
                }
                break;
            }
        }
    }
}

int main(int argc, char *argv[])
{
    printf("[init] bantu_os init starting (PID 1)\n");

    /* TODO: load services from /etc/bantu_os/services.conf or similar */
    (void)argc;
    (void)argv;

    /* Register placeholder services */
    service_register("systemd", "/sbin/init", 0);
    service_register("logger", "/usr/sbin/syslogd", 1);
    service_register("netmanager", "/usr/sbin/netmanager", 1);

    /* Start registered services */
    for (int i = 0; i < registered_count; i++) {
        service_start(service_registry[i].name);
    }

    /* Main loop: reap children and handle signals */
    sigset_t sigs;
    sigemptyset(&sigs);
    sigaddset(&sigs, SIGCHLD);

    while (1) {
        int sig;
        sigwait(&sigs, &sig);
        if (sig == SIGCHLD) {
            reap_children();
        }
    }

    return 0;
}
