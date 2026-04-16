/*
 * Bantu-OS Service Registry
 * 
 * Simple linked list of services with callback pattern.
 * Services are started in order and monitored for failures.
 */

#ifndef BANTU_SERVICES_H
#define BANTU_SERVICES_H

#include <stdbool.h>
#include <stdint.h>
#include <sys/types.h>

/* Service states */
typedef enum {
    SERVICE_STOPPED = 0,
    SERVICE_STARTING,
    SERVICE_RUNNING,
    SERVICE_STOPPING,
    SERVICE_FAILED
} service_state_t;

/* Service start priority - lower numbers start first */
typedef enum {
    PRIORITY_CRITICAL = 0,
    PRIORITY_EARLY = 10,
    PRIORITY_NORMAL = 50,
    PRIORITY_LATE = 100,
    PRIORITY_USER = 200
} service_priority_t;

/* Service configuration callback - returns 0 on success */
typedef int (*service_start_fn)(void);
typedef int (*service_stop_fn)(void);
typedef int (*service_restart_fn)(void);

/* Service descriptor structure */
typedef struct service {
    char name[64];
    char exec_path[256];
    char **argv;
    char **env;
    
    service_priority_t priority;
    service_state_t state;
    uint32_t restart_policy;
    uint32_t max_restarts;
    uint32_t restart_count;
    
    pid_t pid;
    
    service_start_fn on_start;
    service_stop_fn on_stop;
    service_restart_fn on_restart;
    
    struct service *next;
} service_t;

/* Service registry functions */
void service_registry_init(void);
int service_register(service_t *svc);
int service_unregister(const char *name);
service_t *service_find(const char *name);
service_t *service_get_next(service_t *current);
void service_free_registry(void);

/* Service lifecycle */
int start_service(service_t *svc);
int stop_service(service_t *svc);
int restart_service(service_t *svc);
void start_all_services(void);
void stop_all_services(void);

/* Configuration file parsing */
int load_services_from_config(const char *config_path);
int parse_config_line(const char *line, service_t *svc);

/* Service monitoring */
int wait_for_service(service_t *svc, int timeout_ms);
bool is_service_running(const char *name);
int get_service_exit_code(const char *name);

/* Utility functions */
const char *service_state_str(service_state_t state);
void dump_services(void);

#endif
