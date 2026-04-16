/*
 * Bantu-OS Init System
 * 
 * This is the first process that runs after the Linux kernel (PID 1).
 * It mounts essential filesystems and starts system services in order.
 * 
 * Built without systemd - a from-scratch init system.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/reboot.h>
#include <string.h>
#include <fcntl.h>
#include <errno.h>
#include <signal.h>
#include <sys/sysmacros.h>

#include <linux/reboot.h>

#include "services.h"

static void log_init(const char *msg) {
    fprintf(stdout, "[bantu-init] %s\n", msg);
    fflush(stdout);
}

static void log_error(const char *msg) {
    fprintf(stderr, "[bantu-init] ERROR: %s\n", msg);
    fflush(stderr);
}

static int mount_filesystems(void) {
    if (mount("proc", "/proc", "proc", 0, NULL) == -1) {
        log_error("Failed to mount /proc");
        return -1;
    }
    log_init("Mounted /proc");
    
    if (mount("sysfs", "/sys", "sysfs", 0, NULL) == -1) {
        log_error("Failed to mount /sys");
        return -1;
    }
    log_init("Mounted /sys");
    
    if (mount("tmpfs", "/run", "tmpfs", 0, "mode=0755") == -1) {
        log_error("Failed to mount /run");
        return -1;
    }
    log_init("Mounted /run");
    
    if (mount("devpts", "/dev/pts", "devpts", 0, "mode=0620") == -1) {
        log_error("Failed to mount /dev/pts");
        return -1;
    }
    log_init("Mounted /dev/pts");
    
    return 0;
}

static int setup_devices(void) {
    if (mknod("/dev/null", 0666 | S_IFCHR, makedev(1, 3)) == -1 && errno != EEXIST) {
        log_error("Failed to create /dev/null");
        return -1;
    }
    
    if (mknod("/dev/zero", 0666 | S_IFCHR, makedev(1, 5)) == -1 && errno != EEXIST) {
        log_error("Failed to create /dev/zero");
        return -1;
    }
    
    if (mknod("/dev/console", 0600 | S_IFCHR, makedev(5, 1)) == -1 && errno != EEXIST) {
        log_error("Failed to create /dev/console");
        return -1;
    }
    
    return 0;
}

static void handle_sigchld(int sig) {
    (void)sig;
    int status;
    pid_t pid;
    
    while ((pid = waitpid(-1, &status, WNOHANG)) > 0) {
        if (WIFEXITED(status)) {
            fprintf(stdout, "[bantu-init] Service PID %d exited with code %d\n", 
                    pid, WEXITSTATUS(status));
        } else if (WIFSIGNALED(status)) {
            fprintf(stdout, "[bantu-init] Service PID %d killed by signal %d\n", 
                    pid, WTERMSIG(status));
        }
    }
}

static pid_t start_service_exec(const char *path, char *const argv[]) {
    pid_t pid = fork();
    
    if (pid == -1) {
        log_error("fork() failed");
        return -1;
    }
    
    if (pid == 0) {
        execve(path, argv, NULL);
        _exit(127);
    }
    
    return pid;
}

static int run_shell(void) {
    pid_t pid = fork();
    
    if (pid == -1) {
        log_error("Failed to fork for shell");
        return -1;
    }
    
    if (pid == 0) {
        const char *sh_path = "/home/workspace/bantu_os/shell/target/debug/bantu_shell";
        const char *fallback_sh = "/bin/sh";
        
        char *args[] = {(char *)sh_path, NULL};
        
        execve(sh_path, args, NULL);
        
        args[0] = (char *)fallback_sh;
        execve(fallback_sh, args, NULL);
        
        _exit(1);
    }
    
    int status;
    waitpid(pid, &status, 0);
    
    return WEXITSTATUS(status);
}

static void shutdown_system(void) {
    log_init("Shutting down Bantu-OS...");
    sync();
    
    if (reboot(LINUX_REBOOT_CMD_POWER_OFF) == -1) {
        log_error("reboot() failed");
    }
    
    while (1) {
        pause();
    }
}

int main(int argc, char *argv[]) {
    (void)argc;
    (void)argv;
    
    pid_t myself = getpid();
    fprintf(stdout, "\n=== Bantu-OS Init ===\n");
    fprintf(stdout, "[bantu-init] Running as PID %d\n", myself);
    
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = handle_sigchld;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART | SA_NOCLDSTOP;
    
    if (sigaction(SIGCHLD, &sa, NULL) == -1) {
        log_error("Failed to set SIGCHLD handler");
    }
    
    signal(SIGTTIN, SIG_IGN);
    signal(SIGTTOU, SIG_IGN);
    
    log_init("Mounting filesystems...");
    if (mount_filesystems() != 0) {
        log_error("Critical: Failed to mount filesystems");
    }
    
    log_init("Setting up devices...");
    setup_devices();
    
    log_init("Initializing service registry...");
    service_registry_init();
    load_services_from_config("/etc/bantu/services.conf");
    
    log_init("Starting system services...");
    start_all_services();
    
    log_init("Starting AI engine...");
    pid_t ai_pid = start_service_exec("/usr/bin/python3", 
        (char *const[]){"/usr/bin/python3", 
                        "/home/workspace/bantu_os/main.py", NULL});
    (void)ai_pid;
    
    log_init("System initialized. Starting shell...");
    fprintf(stdout, "=== System Ready ===\n\n");
    
    int shell_status = run_shell();
    
    fprintf(stdout, "\n[bantu-init] Shell exited with status %d\n", shell_status);
    
    shutdown_system();
    
    return 0;
}
