/*
 * Bantu-OS Service Registry Implementation
 * 
 * Simple linked list based service management.
 * Services are defined as structs with callback functions.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <errno.h>
#include <signal.h>

#include "services.h"

/* Head of the service linked list */
static service_t *service_list = NULL;
static int service_count = 0;

void service_registry_init(void) {
    service_list = NULL;
    service_count = 0;
    fprintf(stdout, "[services] Registry initialized\n");
}

int service_register(service_t *svc) {
    if (!svc) {
        fprintf(stderr, "[services] ERROR: NULL service passed to register\n");
        return -1;
    }
    
    if (service_find(svc->name) != NULL) {
        fprintf(stderr, "[services] ERROR: Service '%s' already registered\n", svc->name);
        return -1;
    }
    
    service_t *new_svc = malloc(sizeof(service_t));
    if (!new_svc) {
        fprintf(stderr, "[services] ERROR: Failed to allocate service\n");
        return -1;
    }
    
    memcpy(new_svc, svc, sizeof(service_t));
    new_svc->next = NULL;
    new_svc->state = SERVICE_STOPPED;
    new_svc->pid = 0;
    new_svc->restart_count = 0;
    
    if (service_list == NULL) {
        service_list = new_svc;
    } else {
        service_t *current = service_list;
        while (current->next != NULL && current->next->priority < new_svc->priority) {
            current = current->next;
        }
        new_svc->next = current->next;
        current->next = new_svc;
    }
    
    service_count++;
    fprintf(stdout, "[services] Registered: %s (priority=%d)\n", 
            new_svc->name, new_svc->priority);
    
    return 0;
}

int service_unregister(const char *name) {
    if (!name) return -1;
    
    service_t *current = service_list;
    service_t *prev = NULL;
    
    while (current) {
        if (strcmp(current->name, name) == 0) {
            if (current->state == SERVICE_RUNNING) {
                stop_service(current);
            }
            
            if (prev) {
                prev->next = current->next;
            } else {
                service_list = current->next;
            }
            
            free(current);
            service_count--;
            fprintf(stdout, "[services] Unregistered: %s\n", name);
            return 0;
        }
        prev = current;
        current = current->next;
    }
    
    return -1;
}

service_t *service_find(const char *name) {
    if (!name) return NULL;
    
    service_t *current = service_list;
    while (current) {
        if (strcmp(current->name, name) == 0) {
            return current;
        }
        current = current->next;
    }
    
    return NULL;
}

service_t *service_get_next(service_t *current) {
    return current ? current->next : service_list;
}

void service_free_registry(void) {
    service_t *current = service_list;
    service_t *next;
    
    while (current) {
        next = current->next;
        
        if (current->state == SERVICE_RUNNING) {
            stop_service(current);
        }
        
        if (current->argv) {
            free(current->argv);
        }
        if (current->env) {
            free(current->env);
        }
        
        free(current);
        current = next;
    }
    
    service_list = NULL;
    service_count = 0;
}

int start_service(service_t *svc) {
    if (!svc) return -1;
    
    if (svc->state == SERVICE_RUNNING) {
        fprintf(stdout, "[services] %s is already running\n", svc->name);
        return 0;
    }
    
    if (svc->on_start) {
        int ret = svc->on_start();
        if (ret != 0) {
            fprintf(stderr, "[services] %s pre-start callback failed\n", svc->name);
            svc->state = SERVICE_FAILED;
            return -1;
        }
    }
    
    svc->state = SERVICE_STARTING;
    fprintf(stdout, "[services] Starting %s...\n", svc->name);
    
    pid_t pid = fork();
    
    if (pid == -1) {
        fprintf(stderr, "[services] Failed to fork for %s\n", svc->name);
        svc->state = SERVICE_FAILED;
        return -1;
    }
    
    if (pid == 0) {
        if (svc->argv && svc->argv[0]) {
            execve(svc->exec_path, svc->argv, svc->env);
        } else {
            execve(svc->exec_path, NULL, svc->env);
        }
        
        fprintf(stderr, "[services] Failed to exec %s: %s\n", 
                svc->exec_path, strerror(errno));
        _exit(127);
    }
    
    svc->pid = pid;
    svc->state = SERVICE_RUNNING;
    fprintf(stdout, "[services] %s started (PID %d)\n", svc->name, pid);
    
    return 0;
}

int stop_service(service_t *svc) {
    if (!svc) return -1;
    
    if (svc->state != SERVICE_RUNNING) {
        return 0;
    }
    
    svc->state = SERVICE_STOPPING;
    fprintf(stdout, "[services] Stopping %s (PID %d)...\n", svc->name, svc->pid);
    
    if (kill(svc->pid, SIGTERM) == -1) {
        if (errno != ESRCH) {
            fprintf(stderr, "[services] Failed to send SIGTERM to %s\n", svc->name);
        }
    }
    
    int status;
    pid_t ret = waitpid(svc->pid, &status, WNOHANG);
    
    if (ret == 0) {
        usleep(500000);
        
        ret = waitpid(svc->pid, &status, WNOHANG);
        if (ret == 0) {
            fprintf(stdout, "[services] Force killing %s\n", svc->name);
            kill(svc->pid, SIGKILL);
            waitpid(svc->pid, &status, 0);
        }
    }
    
    if (svc->on_stop) {
        svc->on_stop();
    }
    
    svc->state = SERVICE_STOPPED;
    svc->pid = 0;
    
    fprintf(stdout, "[services] %s stopped\n", svc->name);
    return 0;
}

int restart_service(service_t *svc) {
    if (!svc) return -1;
    
    if (svc->on_restart) {
        svc->on_restart();
    }
    
    stop_service(svc);
    return start_service(svc);
}

void start_all_services(void) {
    service_t *current = service_list;
    int started = 0;
    int failed = 0;
    
    fprintf(stdout, "[services] Starting all services...\n");
    
    while (current) {
        if (start_service(current) == 0) {
            started++;
        } else {
            failed++;
        }
        current = current->next;
    }
    
    fprintf(stdout, "[services] Started %d services, %d failed\n", started, failed);
}

void stop_all_services(void) {
    service_t *services[256];
    service_t *current = service_list;
    int count = 0;
    
    while (current && count < 256) {
        services[count++] = current;
        current = current->next;
    }
    
    for (int i = count - 1; i >= 0; i--) {
        if (services[i]->state == SERVICE_RUNNING) {
            stop_service(services[i]);
        }
    }
    
    fprintf(stdout, "[services] All services stopped\n");
}

int parse_config_line(const char *line, service_t *svc) {
    if (!line || !svc) return -1;
    
    if (line[0] == '\n' || line[0] == '#' || line[0] == ';') {
        return -1;
    }
    
    while (*line == ' ' || *line == '\t') line++;
    
    if (*line == '\n' || *line == '#') {
        return -1;
    }
    
    char buffer[512];
    strncpy(buffer, line, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\0';
    
    char *tokens[32];
    int token_count = 0;
    char *saveptr;
    char *token = strtok_r(buffer, ":", &saveptr);
    
    while (token && token_count < 32) {
        tokens[token_count++] = token;
        token = strtok_r(NULL, ":", &saveptr);
    }
    
    if (token_count < 3) {
        fprintf(stderr, "[services] Invalid config line: %s\n", line);
        return -1;
    }
    
    strncpy(svc->name, tokens[0], sizeof(svc->name) - 1);
    strncpy(svc->exec_path, tokens[2], sizeof(svc->exec_path) - 1);
    
    svc->priority = atoi(tokens[1]);
    
    if (token_count > 3) {
        svc->argv = malloc((token_count - 2 + 1) * sizeof(char *));
        if (!svc->argv) return -1;
        
        svc->argv[0] = svc->exec_path;
        for (int i = 3; i < token_count; i++) {
            svc->argv[i - 2] = tokens[i];
        }
        svc->argv[token_count - 2] = NULL;
    } else {
        svc->argv = NULL;
    }
    
    svc->env = NULL;
    return 0;
}

int load_services_from_config(const char *config_path) {
    if (!config_path) return -1;
    
    FILE *f = fopen(config_path, "r");
    if (!f) {
        fprintf(stdout, "[services] No config file at %s, using defaults\n", config_path);
        
        service_t defaults[] = {
            {
                .name = "syslog",
                .exec_path = "/sbin/syslogd",
                .priority = PRIORITY_EARLY,
                .on_start = NULL,
                .on_stop = NULL
            },
            {
                .name = "network",
                .exec_path = "/etc/bantu/network.sh",
                .priority = PRIORITY_NORMAL,
                .on_start = NULL,
                .on_stop = NULL
            }
        };
        
        for (size_t i = 0; i < sizeof(defaults)/sizeof(defaults[0]); i++) {
            service_register(&defaults[i]);
        }
        
        return 0;
    }
    
    char line[512];
    int line_num = 0;
    
    fprintf(stdout, "[services] Loading config from %s\n", config_path);
    
    while (fgets(line, sizeof(line), f)) {
        line_num++;
        
        size_t len = strlen(line);
        if (len > 0 && line[len - 1] == '\n') {
            line[len - 1] = '\0';
        }
        
        service_t svc = {0};
        
        if (parse_config_line(line, &svc) == 0) {
            service_register(&svc);
        }
    }
    
    fclose(f);
    
    fprintf(stdout, "[services] Loaded %d services from config\n", service_count);
    return 0;
}

int wait_for_service(service_t *svc, int timeout_ms) {
    if (!svc) return -1;
    
    int waited = 0;
    int interval = 100;
    
    while (svc->state == SERVICE_STARTING && waited < timeout_ms) {
        usleep(interval * 1000);
        waited += interval;
    }
    
    return (svc->state == SERVICE_RUNNING) ? 0 : -1;
}

bool is_service_running(const char *name) {
    service_t *svc = service_find(name);
    return svc && svc->state == SERVICE_RUNNING;
}

int get_service_exit_code(const char *name) {
    service_t *svc = service_find(name);
    if (!svc || svc->pid <= 0) return -1;
    
    int status;
    pid_t ret = waitpid(svc->pid, &status, WNOHANG);
    
    if (ret == svc->pid && WIFEXITED(status)) {
        return WEXITSTATUS(status);
    }
    
    return -1;
}

const char *service_state_str(service_state_t state) {
    switch (state) {
        case SERVICE_STOPPED:  return "STOPPED";
        case SERVICE_STARTING: return "STARTING";
        case SERVICE_RUNNING:  return "RUNNING";
        case SERVICE_STOPPING: return "STOPPING";
        case SERVICE_FAILED:   return "FAILED";
        default:               return "UNKNOWN";
    }
}

void dump_services(void) {
    fprintf(stdout, "\n=== Service Registry Dump ===\n");
    fprintf(stdout, "Total services: %d\n\n", service_count);
    
    service_t *current = service_list;
    while (current) {
        fprintf(stdout, "  %-20s %-10s PID=%d priority=%d\n",
                current->name,
                service_state_str(current->state),
                current->pid,
                current->priority);
        current = current->next;
    }
    
    fprintf(stdout, "============================\n\n");
}
