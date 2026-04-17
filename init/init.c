/*
 * bantu_os/init/init.c
 * Bantu-OS init system - PID 1, mounts filesystems, starts services.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <sys/wait.h>
#include <sys/mount.h>
#include <sys/sysmacros.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <pwd.h>
#include <sys/utsname.h>
#include <sched.h>

#include "services.h"

#define POWERFALL_SIG SIGTERM

static volatile int running = 1;

void sig_handler(int sig)
{
    (void)sig;
}

int mount_filesystems(void)
{
    printf("[init] mounting filesystems...\n");

    /* Mount /proc (process info) */
    if (access("/proc", F_OK) != 0) {
        if (mount("proc", "/proc", "proc", 0, NULL) != 0)
            perror("[init] mount /proc failed");
    }

    /* Mount /sys (system ABI) */
    if (access("/sys", F_OK) != 0) {
        if (mount("sysfs", "/sys", "sysfs", 0, NULL) != 0)
            perror("[init] mount /sys failed");
    }

    /* Mount /run (tmpfs runtime) */
    if (access("/run", F_OK) != 0) {
        if (mount("tmpfs", "/run", "tmpfs", 0, NULL) != 0)
            perror("[init] mount /run failed");
    }

    /* Mount /dev/pts (pseudo-terminals) */
    if (access("/dev/pts", F_OK) != 0) {
        if (mount("devpts", "/dev/pts", "devpts", 0, NULL) != 0)
            perror("[init] mount /dev/pts failed");
    }

    printf("[init] filesystems mounted\n");
    return 0;
}

int create_device_nodes(void)
{
    printf("[init] creating device nodes...\n");

    /* /dev/null */
    if (access("/dev/null", F_OK) != 0) {
        unlink("/dev/null");
        mknod("/dev/null", S_IFCHR | 0666, makedev(1, 3));
    }

    /* /dev/zero */
    if (access("/dev/zero", F_OK) != 0) {
        unlink("/dev/zero");
        mknod("/dev/zero", S_IFCHR | 0666, makedev(1, 5));
    }

    /* /dev/console */
    if (access("/dev/console", F_OK) != 0) {
        unlink("/dev/console");
        mknod("/dev/console", S_IFCHR | 0600, makedev(5, 1));
    }

    printf("[init] device nodes ready\n");
    return 0;
}

void setup_signals(void)
{
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = sig_handler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART;

    sigaction(SIGTERM, &sa, NULL);
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGCHLD, &sa, NULL);
    sigaction(SIGPIPE, &sa, NULL);
}

int setup_hostname(void)
{
    FILE *fp = fopen("/etc/hostname", "r");
    if (fp) {
        char hostname[256];
        if (fgets(hostname, sizeof(hostname), fp))
            hostname[strcspn(hostname, "\n")] = 0;
        sethostname(hostname, strlen(hostname));
        fclose(fp);
    }
    return 0;
}

int drop_privileges(void)
{
    struct passwd *pw = getpwnam("nobody");
    if (!pw)
        pw = getpwnam("daemon");
    if (pw) {
        setuid(pw->pw_uid);
        setgid(pw->pw_gid);
    }
    return 0;
}

int run_shell(void)
{
    printf("[init] launching shell...\n");

    pid_t pid = fork();
    if (pid == 0) {
        /* Child: exec shell */
        execl("/bin/sh", "/bin/sh", (char *)NULL);
        _exit(127);
    } else if (pid > 0) {
        /* Wait for shell to exit */
        waitpid(pid, NULL, 0);
    }

    return 0;
}

int shutdown_system(void)
{
    printf("[init] initiating shutdown...\n");

    stop_all_services();
    sync();

    printf("[init] rebooting...\n");
    reboot(RB_POWER_OFF);

    return 0;
}

void main_loop(void)
{
    sigset_t sigs;
    sigemptyset(&sigs);
    sigaddset(&sigs, SIGCHLD);

    while (running) {
        int sig;
        int ret = sigwait(&sigs, &sig);
        if (ret == 0 && sig == SIGCHLD) {
            reap_service_children();
        }
    }
}

int main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;

    printf("\n[init] Bantu-OS init starting (PID 1)\n");

    /* 1. Setup signals */
    setup_signals();

    /* 2. Mount filesystems */
    mount_filesystems();

    /* 3. Create device nodes */
    create_device_nodes();

    /* 4. Set hostname */
    setup_hostname();

    /* 5. Initialize service registry */
    service_registry_init();

    /* 6. Load services from config (fallback to defaults) */
    if (access("/etc/bantu/services.conf", R_OK) == 0) {
        printf("[init] loading services from /etc/bantu/services.conf\n");
        load_services_from_config("/etc/bantu/services.conf");
    } else {
        printf("[init] no config found, using built-in defaults\n");

        service_t svc;

        /* syslog - early priority */
        memset(&svc, 0, sizeof(svc));
        strcpy(svc.name, "syslog");
        strcpy(svc.exec_path, "/sbin/syslogd");
        svc.priority = PRIORITY_EARLY;
        svc.restart_policy = RESTART_ALWAYS;
        service_register(&svc);

        /* network - normal priority */
        memset(&svc, 0, sizeof(svc));
        strcpy(svc.name, "network");
        strcpy(svc.exec_path, "/sbin/netmanager");
        svc.priority = PRIORITY_NORMAL;
        svc.restart_policy = RESTART_ALWAYS;
        service_register(&svc);
    }

    dump_services();

    /* 7. Start all services */
    start_all_services();

    /* 8. Drop privileges and run shell (or hand off to AI shell) */
    drop_privileges();

    /* Check if AI shell exists and use it */
    if (access("/home/workspace/bantu_os/shell/target/debug/bantu_shell", F_OK) == 0) {
        printf("[init] launching AI shell...\n");
        pid_t pid = fork();
        if (pid == 0) {
            execl("/home/workspace/bantu_os/shell/target/debug/bantu_shell",
                  "bantu_shell", (char *)NULL);
            _exit(127);
        }
    } else {
        run_shell();
    }

    /* 9. Main loop: reap children, handle signals */
    main_loop();

    /* 10. Shutdown */
    shutdown_system();

    return 0;
}