/*
 * bantu_os/init/services.c
 * Service registry implementation - linked list based service management.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <signal.h>

#include "services.h"

/* Head of service linked list */
static service_t *service_list = NULL;
static int svc_count = 0;

/* Initialize the service registry */
void service_registry_init(void)
{
    service_list = NULL;
    svc_count = 0;
}

/* Allocate and register a service */
int service_register(service_t *svc)
{
    if (!svc || !svc->name[0] || !svc->exec_path[0])
        return -1;

    service_t *new_svc = malloc(sizeof(service_t));
    if (!new_svc)
        return -1;

    memcpy(new_svc, svc, sizeof(service_t));
    new_svc->next = NULL;
    new_svc->pid = -1;
    new_svc->state = SERVICE_STOPPED;
    new_svc->restart_count = 0;

    /* Append to linked list */
    if (service_list == NULL) {
        service_list = new_svc;
    } else {
        service_t *cur = service_list;
        while (cur->next)
            cur = cur->next;
        cur->next = new_svc;
    }

    svc_count++;
    printf("[init] registered service: %s (priority=%d)\n",
           new_svc->name, new_svc->priority);
    return 0;
}

/* Find service by name */
service_t *service_find(const char *name)
{
    service_t *cur = service_list;
    while (cur) {
        if (strcmp(cur->name, name) == 0)
            return cur;
        cur = cur->next;
    }
    return NULL;
}

/* Remove service by name */
int service_unregister(const char *name)
{
    service_t *cur = service_list;
    service_t *prev = NULL;

    while (cur) {
        if (strcmp(cur->name, name) == 0) {
            if (prev)
                prev->next = cur->next;
            else
                service_list = cur->next;
            free(cur);
            svc_count--;
            return 0;
        }
        prev = cur;
        cur = cur->next;
    }
    return -1;
}

/* Free entire registry */
void service_free_registry(void)
{
    service_t *cur = service_list;
    while (cur) {
        service_t *next = cur->next;
        free(cur);
        cur = next;
    }
    service_list = NULL;
    svc_count = 0;
}

int service_count(void)
{
    return svc_count;
}

/* Start a single service */
int start_service(service_t *svc)
{
    if (!svc)
        return -1;
    if (svc->state == SERVICE_RUNNING)
        return 0;

    /* Run pre-start callback */
    if (svc->on_start) {
        if (svc->on_start() != 0) {
            svc->state = SERVICE_FAILED;
            return -1;
        }
    }

    pid_t pid = fork();
    if (pid == 0) {
        /* Child process */
        if (svc->argc > 0) {
            execve(svc->exec_path, svc->argv, NULL);
        } else {
            execl(svc->exec_path, svc->exec_path, (char *)NULL);
        }
        _exit(127);
    } else if (pid > 0) {
        svc->pid = pid;
        svc->state = SERVICE_RUNNING;
        printf("[init] started %s (pid %d)\n", svc->name, pid);
        return 0;
    }

    perror("[init] fork failed");
    return -1;
}

/* Stop a single service */
int stop_service(service_t *svc)
{
    if (!svc || svc->state != SERVICE_RUNNING)
        return -1;

    if (svc->on_stop)
        svc->on_stop();

    svc->state = SERVICE_STOPPING;
    if (kill(svc->pid, SIGTERM) != 0) {
        perror("[init] SIGTERM failed");
        return -1;
    }

    int status;
    if (waitpid(svc->pid, &status, 0) < 0)
        perror("[init] waitpid failed");

    svc->state = SERVICE_STOPPED;
    svc->pid = -1;
    printf("[init] stopped %s\n", svc->name);
    return 0;
}

/* Restart a service */
int restart_service(service_t *svc)
{
    if (!svc)
        return -1;

    if (svc->on_restart)
        svc->on_restart();

    if (svc->state == SERVICE_RUNNING)
        stop_service(svc);

    return start_service(svc);
}

/* Start all services in priority order */
void start_all_services(void)
{
    printf("[init] starting all services...\n");

    service_t *cur = service_list;
    while (cur) {
        if (cur->priority <= PRIORITY_NORMAL) {
            start_service(cur);
        }
        cur = cur->next;
    }

    cur = service_list;
    while (cur) {
        if (cur->priority > PRIORITY_NORMAL && cur->priority <= PRIORITY_LATE) {
            start_service(cur);
        }
        cur = cur->next;
    }

    cur = service_list;
    while (cur) {
        if (cur->priority > PRIORITY_LATE) {
            start_service(cur);
        }
        cur = cur->next;
    }
}

/* Stop all services in reverse priority order */
void stop_all_services(void)
{
    printf("[init] stopping all services...\n");

    /* Collect services into array for reverse iteration */
    service_t *services[256];
    int n = 0;
    service_t *cur = service_list;
    while (cur && n < 256) {
        services[n++] = cur;
        cur = cur->next;
    }

    for (int i = n - 1; i >= 0; i--) {
        if (services[i]->state == SERVICE_RUNNING)
            stop_service(services[i]);
    }
}

/* Reap zombie children, handle auto-restart */
void reap_service_children(void)
{
    int status;
    pid_t pid;

    while ((pid = waitpid(-1, &status, WNOHANG)) > 0) {
        service_t *svc = service_list;
        while (svc) {
            if (svc->pid == pid) {
                svc->exit_code = WEXITSTATUS(status);
                printf("[init] %s exited (code %d)\n",
                       svc->name, svc->exit_code);

                if (svc->restart_policy == RESTART_ALWAYS ||
                    (svc->restart_policy == RESTART_ON_FAILURE &&
                     svc->restart_count < svc->max_restarts)) {
                    svc->restart_count++;
                    printf("[init] auto-restarting %s\n", svc->name);
                    sleep(1);
                    start_service(svc);
                } else {
                    svc->state = SERVICE_STOPPED;
                    svc->pid = -1;
                }
                break;
            }
            svc = svc->next;
        }
    }
}

/* Load services from config file */
int load_services_from_config(const char *path)
{
    FILE *fp = fopen(path, "r");
    if (!fp) {
        perror("[init] failed to open config");
        return -1;
    }

    char line[512];
    while (fgets(line, sizeof(line), fp)) {
        /* Strip newline */
        line[strcspn(line, "\n")] = 0;

        /* Skip empty lines and comments */
        if (line[0] == '#' || line[0] == ';' || line[0] == 0)
            continue;

        service_t svc = {0};
        if (parse_config_line(line, &svc) == 0)
            service_register(&svc);
    }

    fclose(fp);
    return 0;
}

/* Parse a single config line: name:priority:path[:arg1:arg2:...] */
int parse_config_line(const char *line, service_t *svc)
{
    memset(svc, 0, sizeof(service_t));

    char copy[512];
    strncpy(copy, line, sizeof(copy) - 1);

    char *fields[32];
    int n = 0;
    char *token = strtok(copy, ":");
    while (token && n < 32) {
        fields[n++] = token;
        token = strtok(NULL, ":");
    }

    if (n < 3)
        return -1;

    strncpy(svc->name, fields[0], MAX_SERVICE_NAME - 1);
    svc->priority = atoi(fields[1]);
    strncpy(svc->exec_path, fields[2], MAX_SERVICE_PATH - 1);
    svc->restart_policy = RESTART_ON_FAILURE;
    svc->max_restarts = 3;

    /* Parse extra args */
    for (int i = 3; i < n && svc->argc < MAX_ARGS - 1; i++) {
        svc->argv[svc->argc++] = strdup(fields[i]);
    }

    return 0;
}

/* Monitoring */
int is_service_running(const char *name)
{
    service_t *svc = service_find(name);
    return svc && svc->state == SERVICE_RUNNING;
}

int get_service_exit_code(const char *name)
{
    service_t *svc = service_find(name);
    return svc ? svc->exit_code : -1;
}

/* Utility */
const char *service_state_str(service_state_t state)
{
    static const char *names[] = {
        "STOPPED", "STARTING", "RUNNING", "STOPPING", "FAILED"
    };
    return names[state % 5];
}

const char *service_priority_str(service_priority_t prio)
{
    switch (prio) {
        case PRIORITY_CRITICAL: return "CRITICAL";
        case PRIORITY_EARLY:    return "EARLY";
        case PRIORITY_NORMAL:    return "NORMAL";
        case PRIORITY_LATE:      return "LATE";
        case PRIORITY_USER:      return "USER";
        default:                 return "UNKNOWN";
    }
}

void dump_services(void)
{
    printf("[init] service registry (%d services):\n", svc_count);
    service_t *cur = service_list;
    while (cur) {
        printf("  %s: state=%s prio=%d pid=%d restart=%s\n",
               cur->name,
               service_state_str(cur->state),
               cur->priority,
               (int)cur->pid,
               (cur->restart_policy == RESTART_ALWAYS) ? "always" :
               (cur->restart_policy == RESTART_ON_FAILURE) ? "on-failure" : "none");
        cur = cur->next;
    }
}