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
#include <errno.h>
#include <sys/un.h>
#include "services.h"
#include "registry_socket.h"

static volatile sig_atomic_t running = 1;
static pid_t shell_pid = -1;
static int registry_fd = -1;
static const char *registry_path = "/run/bantu/init.sock";

static const char *get_registry_path(void)
{
    const char *override = getenv("BANTU_INIT_REGISTRY_SOCKET");
    return override && override[0] ? override : registry_path;
}
static const char *get_shell_path(void)
{
    const char *override = getenv("BANTU_INIT_SHELL_PATH");
    return override && override[0] ? override : NULL;
}

int mount_filesystems(void)
{
    if (getenv("BANTU_INIT_SKIP_MOUNTS"))
        return 0;

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
    struct sigaction ignore;
    sigset_t blocked;

    memset(&ignore, 0, sizeof(ignore));
    ignore.sa_handler = SIG_IGN;
    sigemptyset(&ignore.sa_mask);
    if (sigaction(SIGPIPE, &ignore, NULL) != 0)
        perror("[init] sigaction SIGPIPE failed");

    sigemptyset(&blocked);
    sigaddset(&blocked, SIGTERM);
    sigaddset(&blocked, SIGINT);
    sigaddset(&blocked, SIGCHLD);
    if (sigprocmask(SIG_BLOCK, &blocked, NULL) != 0)
        perror("[init] sigprocmask failed");
}

int setup_hostname(void)
{
    FILE *fp = fopen("/etc/hostname", "r");
    if (fp) {
        char hostname[256] = {0};
        if (fgets(hostname, sizeof(hostname), fp)) {
            hostname[strcspn(hostname, "\r\n")] = 0;
            if (hostname[0] && sethostname(hostname, strlen(hostname)) != 0)
                perror("[init] sethostname failed");
        }
        fclose(fp);
    }
    return 0;
}

int run_shell(void)
{
    printf("[init] launching shell...\n");

    shell_pid = fork();
    if (shell_pid == 0) {
        sigset_t unblocked;
        sigemptyset(&unblocked);
        sigprocmask(SIG_SETMASK, &unblocked, NULL);
        execl("/bin/sh", "/bin/sh", (char *)NULL);
        _exit(127);
    }
    if (shell_pid < 0) {
        perror("[init] fork shell failed");
        shell_pid = -1;
        return -1;
    }

    return 0;
}

int shutdown_system(void)
{
    printf("[init] initiating shutdown...\n");

    stop_all_services();
    sync();

    if (shell_pid > 0) {
        int status;
        pid_t result = waitpid(shell_pid, &status, WNOHANG);
        if (result == 0) {
            kill(shell_pid, SIGTERM);
            waitpid(shell_pid, NULL, 0);
        }
        shell_pid = -1;
    }

    printf("[init] rebooting...\n");
    if (reboot(RB_POWER_OFF) != 0) {
        perror("[init] reboot failed");
        return -1;
    }

    return 0;
}

void main_loop(void)
{
    sigset_t sigs;
    sigemptyset(&sigs);
    sigaddset(&sigs, SIGTERM);
    sigaddset(&sigs, SIGINT);
    sigaddset(&sigs, SIGCHLD);

    while (running) {
        if (registry_fd >= 0)
            registry_socket_poll(registry_fd, 100);

        int sig;
        siginfo_t info;
        struct timespec timeout = {0, 0};
        int ret = sigtimedwait(&sigs, &info, &timeout);
        if (ret < 0) {
            if (errno == EAGAIN || errno == EINTR)
                continue;
            continue;
        }
        sig = ret;
        if (sig == SIGCHLD) {
            reap_service_children();
            if (shell_pid > 0) {
                int status;
                pid_t result = waitpid(shell_pid, &status, WNOHANG);
                if (result == shell_pid)
                    shell_pid = -1;
            }
        } else if (sig == SIGTERM || sig == SIGINT) {
            running = 0;
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
        strcpy(svc.exec_path, "/bin/true");
        svc.priority = PRIORITY_EARLY;
        svc.restart_policy = RESTART_NONE;
        service_register(&svc);

        /* network - normal priority */
        memset(&svc, 0, sizeof(svc));
        strcpy(svc.name, "network");
        strcpy(svc.exec_path, "/bin/true");
        svc.priority = PRIORITY_NORMAL;
        svc.restart_policy = RESTART_NONE;
        service_register(&svc);
    }

    dump_services();

    /* 7. Start all services */
    start_all_services();

    const char *active_registry_path = get_registry_path();
    char registry_dir[sizeof(((struct sockaddr_un *)0)->sun_path)] = {0};
    strncpy(registry_dir, active_registry_path, sizeof(registry_dir) - 1);
    char *last_slash = strrchr(registry_dir, '/');
    if (last_slash && last_slash != registry_dir) {
        *last_slash = '\0';
        mkdir(registry_dir, 0755);
    }
    registry_fd = registry_socket_start(active_registry_path);
    if (registry_fd < 0)
        perror("[init] registry socket unavailable");
    else
        printf("[init] registry socket listening at %s\n", active_registry_path);

    /* 8. Run shell while retaining root as PID 1 */
    const char *shell_path = get_shell_path();
    if (shell_path == NULL && access("/home/workspace/bantu_os/shell/target/release/bantu", F_OK) == 0) {
        shell_path = "/home/workspace/bantu_os/shell/target/release/bantu";
    } else if (shell_path == NULL && access("/home/workspace/bantu_os/shell/target/debug/bantu", F_OK) == 0) {
        shell_path = "/home/workspace/bantu_os/shell/target/debug/bantu";
    }

    if (shell_path != NULL) {
        printf("[init] launching AI shell: %s\n", shell_path);
        shell_pid = fork();
        if (shell_pid == 0) {
            sigset_t unblocked;
            sigemptyset(&unblocked);
            sigprocmask(SIG_SETMASK, &unblocked, NULL);
            execl(shell_path, "bantu", (char *)NULL);
            _exit(127);
        }
        if (shell_pid < 0) {
            perror("[init] fork AI shell failed");
            shell_pid = -1;
        }
    } else {
        run_shell();
    }

    /* 9. Main loop: reap children, handle signals */
    main_loop();

    /* 10. Shutdown */
    registry_socket_close(registry_fd, get_registry_path());
    shutdown_system();

    return 0;
}