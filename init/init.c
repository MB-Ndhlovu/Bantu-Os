/*
 * Bantu-OS Init System
 * Layer 1: PID 1 - Service Registry and Manager
 *
 * This is a minimal init system written in C.
 * It runs as PID 1 and manages system services.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <signal.h>

#define MAX_SERVICES 32
#define MAX_SERVICE_NAME 64
#define MAX_SERVICE_CMD 256

typedef enum {
    SERVICE_STOPPED = 0,
    SERVICE_STARTING,
    SERVICE_RUNNING,
    SERVICE_STOPPING
} ServiceState;

typedef struct {
    char name[MAX_SERVICE_NAME];
    char command[MAX_SERVICE_CMD];
    pid_t pid;
    ServiceState state;
    int auto_start;  /* 1 if should start at boot */
} Service;

static Service services[MAX_SERVICES];
static int service_count = 0;
static volatile int running = 1;

/* Logging */
void log_msg(const char *level, const char *fmt, ...) {
    fprintf(stdout, "[%s] ", level);
    va_list args;
    va_start(args, fmt);
    vfprintf(stdout, fmt, args);
    va_end(args);
    fprintf(stdout, "\n");
    fflush(stdout);
}

#define LOG(fmt, ...) log_msg("INFO", fmt, ##__VA_ARGS__)
#define WARN(fmt, ...) log_msg("WARN", fmt, ##__VA_ARGS__)
#define ERR(fmt, ...) log_msg("ERROR", fmt, ##__VA_ARGS__)

/* Register a service */
int service_register(const char *name, const char *command, int auto_start) {
    if (service_count >= MAX_SERVICES) {
        ERR("Service registry full (max %d)", MAX_SERVICES);
        return -1;
    }
    if (strlen(name) >= MAX_SERVICE_NAME || strlen(command) >= MAX_SERVICE_CMD) {
        ERR("Service name or command too long");
        return -1;
    }

    Service *svc = &services[service_count];
    strncpy(svc->name, name, MAX_SERVICE_NAME - 1);
    strncpy(svc->command, command, MAX_SERVICE_CMD - 1);
    svc->pid = -1;
    svc->state = SERVICE_STOPPED;
    svc->auto_start = auto_start;

    service_count++;
    LOG("Registered service: %s -> %s", name, command);
    return service_count - 1;
}

/* Start a service */
int service_start(const char *name) {
    for (int i = 0; i < service_count; i++) {
        if (strcmp(services[i].name, name) == 0) {
            if (services[i].state == SERVICE_RUNNING) {
                WARN("Service %s already running (PID %d)", name, services[i].pid);
                return 0;
            }

            services[i].state = SERVICE_STARTING;
            pid_t pid = fork();

            if (pid < 0) {
                ERR("fork() failed for service %s: %s", name, strerror(errno));
                services[i].state = SERVICE_STOPPED;
                return -1;
            }

            if (pid == 0) {
                /* Child process: exec the command */
                close(STDIN_FILENO);
                close(STDOUT_FILENO);
                close(STDERR_FILENO);

                open("/dev/null", O_RDONLY);  /* stdin */
                open("/dev/null", O_WRONLY);  /* stdout */
                open("/dev/null", O_WRONLY);  /* stderr */

                setsid();

                char *argv[] = {"/bin/sh", "-c", services[i].command, NULL};
                execvp("/bin/sh", argv);
                _exit(127);
            }

            services[i].pid = pid;
            services[i].state = SERVICE_RUNNING;
            LOG("Started service: %s (PID %d)", name, pid);
            return 0;
        }
    }
    ERR("Service not found: %s", name);
    return -1;
}

/* Stop a service */
int service_stop(const char *name) {
    for (int i = 0; i < service_count; i++) {
        if (strcmp(services[i].name, name) == 0) {
            if (services[i].state == SERVICE_STOPPED) {
                WARN("Service %s already stopped", name);
                return 0;
            }

            services[i].state = SERVICE_STOPPING;
            if (services[i].pid > 0) {
                kill(services[i].pid, SIGTERM);
                usleep(100000);  /* 100ms grace */

                if (kill(services[i].pid, 0) == 0) {
                    kill(services[i].pid, SIGKILL);
                }
                waitpid(services[i].pid, NULL, WNOHANG);
            }

            services[i].state = SERVICE_STOPPED;
            services[i].pid = -1;
            LOG("Stopped service: %s", name);
            return 0;
        }
    }
    ERR("Service not found: %s", name);
    return -1;
}

/* Restart a service */
int service_restart(const char *name) {
    service_stop(name);
    return service_start(name);
}

/* List all services and their status */
void service_list(void) {
    printf("Bantu-OS Service Registry (%d services):\n", service_count);
    printf("%-20s %-10s %-10s %s\n", "NAME", "STATE", "PID", "COMMAND");
    printf("----------------------------------------------------------------------\n");
    for (int i = 0; i < service_count; i++) {
        const char *state_str;
        switch (services[i].state) {
            case SERVICE_STOPPED:   state_str = "STOPPED"; break;
            case SERVICE_STARTING:   state_str = "STARTING"; break;
            case SERVICE_RUNNING:    state_str = "RUNNING"; break;
            case SERVICE_STOPPING:   state_str = "STOPPING"; break;
            default:                 state_str = "UNKNOWN"; break;
        }
        printf("%-20s %-10s %-10d %s\n",
               services[i].name,
               state_str,
               services[i].pid,
               services[i].command);
    }
}

/* Reap zombie children */
void reap_children(void) {
    int status;
    pid_t pid;
    while ((pid = waitpid(-1, &status, WNOHANG)) > 0) {
        /* Find which service this belonged to */
        for (int i = 0; i < service_count; i++) {
            if (services[i].pid == pid) {
                if (services[i].state == SERVICE_RUNNING) {
                    LOG("Service %s died unexpectedly (PID %d), restarting...", services[i].name, pid);
                    services[i].pid = -1;
                    services[i].state = SERVICE_STOPPED;
                    if (services[i].auto_start) {
                        service_start(services[i].name);
                    }
                } else {
                    services[i].pid = -1;
                    services[i].state = SERVICE_STOPPED;
                }
                break;
            }
        }
    }
}

/* Signal handler */
void signal_handler(int sig) {
    switch (sig) {
        case SIGTERM:
            LOG("Received SIGTERM, shutting down...");
            running = 0;
            for (int i = 0; i < service_count; i++) {
                if (services[i].state == SERVICE_RUNNING) {
                    service_stop(services[i].name);
                }
            }
            LOG("All services stopped. Bantu-OS init exiting.");
            exit(0);
            break;
        case SIGCHLD:
            reap_children();
            break;
    }
}

/* Init shell for interactive commands */
void init_shell(void) {
    char line[256];

    printf("\nBantu-OS Init Shell (PID 1)\n");
    printf("Commands: register, start, stop, restart, list, help, exit\n\n");

    while (running) {
        printf("init> ");
        fflush(stdout);

        if (fgets(line, sizeof(line), stdin) == NULL) {
            break;
        }

        /* Remove trailing newline */
        size_t len = strlen(line);
        if (len > 0 && line[len-1] == '\n') line[len-1] = '\0';

        if (strlen(line) == 0) continue;

        char cmd[32], arg1[64], arg2[128];
        int n = sscanf(line, "%31s %63s %255[^\n]", cmd, arg1, arg2);

        if (strcmp(cmd, "help") == 0 || strcmp(cmd, "?") == 0) {
            printf("Commands:\n");
            printf("  register <name> <command> [auto:0|1]  - Register a new service\n");
            printf("  start <name>                         - Start a service\n");
            printf("  stop <name>                          - Stop a service\n");
            printf("  restart <name>                       - Restart a service\n");
            printf("  list                                  - List all services\n");
            printf("  exit                                  - Shutdown and exit\n");
            printf("  help                                  - Show this help\n");
        } else if (strcmp(cmd, "list") == 0) {
            service_list();
        } else if (strcmp(cmd, "exit") == 0 || strcmp(cmd, "quit") == 0) {
            running = 0;
            for (int i = 0; i < service_count; i++) {
                if (services[i].state == SERVICE_RUNNING) {
                    service_stop(services[i].name);
                }
            }
            LOG("Bantu-OS init exiting.");
            break;
        } else if (strcmp(cmd, "register") == 0) {
            if (n < 3) {
                printf("Usage: register <name> <command> [auto:0|1]\n");
            } else {
                int auto_start = (n >= 4) ? atoi(arg2) : 0;
                if (service_register(arg1, arg2, auto_start) >= 0) {
                    printf("Service registered: %s\n", arg1);
                }
            }
        } else if (strcmp(cmd, "start") == 0) {
            if (n < 2) {
                printf("Usage: start <name>\n");
            } else {
                service_start(arg1);
            }
        } else if (strcmp(cmd, "stop") == 0) {
            if (n < 2) {
                printf("Usage: stop <name>\n");
            } else {
                service_stop(arg1);
            }
        } else if (strcmp(cmd, "restart") == 0) {
            if (n < 2) {
                printf("Usage: restart <name>\n");
            } else {
                service_restart(arg1);
            }
        } else {
            printf("Unknown command: %s. Type 'help' for commands.\n", cmd);
        }
    }
}

/* Boot: register default services and start auto-start ones */
void boot(void) {
    LOG("Bantu-OS Init starting...");

    /* Register default services */
    service_register("logging", "/usr/sbin/syslogd -n", 1);
    service_register("network", "/sbin/networking start", 1);
    service_register("python-engine", "python3 -m bantu_os", 1);

    /* Start auto-start services */
    for (int i = 0; i < service_count; i++) {
        if (services[i].auto_start) {
            service_start(services[i].name);
        }
    }

    LOG("Boot complete. %d services registered.", service_count);
}

int main(int argc, char *argv[]) {
    /* Set signals */
    signal(SIGTERM, signal_handler);
    signal(SIGCHLD, signal_handler);
    signal(SIGINT, SIG_IGN);

    /* Check if we're PID 1 (real init) or being run directly */
    if (getpid() == 1) {
        /* We are PID 1 — boot sequence */
        boot();
    } else {
        /* Running in userspace — show info */
        printf("Bantu-OS Init (userspace mode)\n");
        printf("Note: For full init functionality, run as PID 1.\n\n");
    }

    /* Interactive shell */
    init_shell();

    return 0;
}