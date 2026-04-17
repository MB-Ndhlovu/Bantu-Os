/*
 * bantu_os/init/services.h
 * Service registry header - defines the service structure and API.
 */

#ifndef BANTU_SERVICES_H
#define BANTU_SERVICES_H

#include <stdint.h>
#include <sys/types.h>

#define MAX_SERVICE_NAME 64
#define MAX_SERVICE_PATH 256
#define MAX_ARGS 16

/* Service priority levels */
typedef enum {
    PRIORITY_CRITICAL = 0,    /* Filesystem mounting, internal only */
    PRIORITY_EARLY = 10,      /* syslog, early logging */
    PRIORITY_NORMAL = 50,     /* network, system services */
    PRIORITY_LATE = 100,      /* User services, GUI */
    PRIORITY_USER = 200       /* User-specific startup */
} service_priority_t;

/* Service states */
typedef enum {
    SERVICE_STOPPED = 0,
    SERVICE_STARTING,
    SERVICE_RUNNING,
    SERVICE_STOPPING,
    SERVICE_FAILED
} service_state_t;

/* Restart policies */
typedef enum {
    RESTART_NONE = 0,
    RESTART_ON_FAILURE,
    RESTART_ALWAYS
} restart_policy_t;

/* Service callback types */
typedef int (*service_start_fn)(void);
typedef int (*service_stop_fn)(void);
typedef int (*service_restart_fn)(void);

/* Service structure - linked list node */
typedef struct service {
    char name[MAX_SERVICE_NAME];
    char exec_path[MAX_SERVICE_PATH];
    char *argv[MAX_ARGS];
    int argc;
    
    service_priority_t priority;
    service_state_t state;
    restart_policy_t restart_policy;
    uint32_t max_restarts;
    uint32_t restart_count;
    
    pid_t pid;
    int exit_code;
    
    /* Callbacks */
    service_start_fn on_start;
    service_stop_fn on_stop;
    service_restart_fn on_restart;
    
    /* Linked list */
    struct service *next;
} service_t;

/* Registry API */
void service_registry_init(void);
int service_register(service_t *svc);
int service_unregister(const char *name);
service_t *service_find(const char *name);
void service_free_registry(void);
int service_count(void);

/* Lifecycle API */
int start_service(service_t *svc);
int stop_service(service_t *svc);
int restart_service(service_t *svc);
void start_all_services(void);
void stop_all_services(void);

/* Configuration API */
int load_services_from_config(const char *path);
int parse_config_line(const char *line, service_t *svc);

/* Monitoring API */
int wait_for_service(service_t *svc, int timeout_ms);
int is_service_running(const char *name);
int get_service_exit_code(const char *name);

/* Reap children - called from main loop */
void reap_service_children(void);

/* Utility API */
const char *service_state_str(service_state_t state);
const char *service_priority_str(service_priority_t prio);
void dump_services(void);

#endif /* BANTU_SERVICES_H */