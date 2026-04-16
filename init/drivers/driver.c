/*
 * Bantu-OS Device Driver Core Implementation
 * Layer 2: Driver registry, null/zero/TTY devices
 */
#define _POSIX_C_SOURCE 200809L
#include "driver.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <pthread.h>

/* ---- Driver registry ---- */
#define MAX_DRIVERS 32
static struct bantu_driver *g_driver_registry[MAX_DRIVERS];
static int g_driver_count = 0;
static pthread_mutex_t g_registry_lock = PTHREAD_MUTEX_INITIALIZER;

int bantu_driver_register(struct bantu_driver *drv) {
    if (!drv || !drv->name) return BANTU_DRV_ERR;
    pthread_mutex_lock(&g_registry_lock);
    if (g_driver_count >= MAX_DRIVERS) {
        pthread_mutex_unlock(&g_registry_lock);
        return BANTU_DRV_NOMEM;
    }
    g_driver_registry[g_driver_count++] = drv;
    pthread_mutex_unlock(&g_registry_lock);
    return BANTU_DRV_OK;
}

int bantu_driver_unregister(const char *name) {
    pthread_mutex_lock(&g_registry_lock);
    for (int i = 0; i < g_driver_count; i++) {
        if (strcmp(g_driver_registry[i]->name, name) == 0) {
            memmove(&g_driver_registry[i], &g_driver_registry[i+1],
                (g_driver_count - i - 1) * sizeof(void *));
            g_driver_count--;
            pthread_mutex_unlock(&g_registry_lock);
            return BANTU_DRV_OK;
        }
    }
    pthread_mutex_unlock(&g_registry_lock);
    return BANTU_DRV_ERR;
}

struct bantu_driver *bantu_driver_find(const char *name) {
    for (int i = 0; i < g_driver_count; i++)
        if (strcmp(g_driver_registry[i]->name, name) == 0)
            return g_driver_registry[i];
    return NULL;
}

int bantu_driver_init_all(void) {
    int ok = 0;
    for (int i = 0; i < g_driver_count; i++) {
        struct bantu_driver *d = g_driver_registry[i];
        if (d->init) {
            int r = d->init(d);
            d->status = (r == BANTU_DRV_OK) ? BANTU_DRV_OK : BANTU_DRV_ERR;
            if (r == BANTU_DRV_OK) ok++;
        }
    }
    return ok;
}

void bantu_driver_shutdown_all(void) {
    for (int i = 0; i < g_driver_count; i++) {
        struct bantu_driver *d = g_driver_registry[i];
        if (d->shutdown) d->shutdown(d);
    }
}

/* ---- NULL device ---- */
static int g_null_fd = -1;

static int null_init(struct bantu_driver *drv) {
    (void)drv;
    g_null_fd = open("/dev/null", O_RDWR);
    if (g_null_fd < 0) g_null_fd = 3;
    return g_null_fd >= 0 ? BANTU_DRV_OK : BANTU_DRV_ERR;
}

static void null_shutdown(struct bantu_driver *drv) {
    (void)drv;
    if (g_null_fd >= 0) { close(g_null_fd); g_null_fd = -1; }
}

static ssize_t null_read(struct bantu_driver *drv, void *buf, size_t count, long offset) {
    (void)drv; (void)offset;
    memset(buf, 0, count);
    return (ssize_t)count;
}

static ssize_t null_write(struct bantu_driver *drv, const void *buf, size_t count, long offset) {
    (void)drv; (void)offset; (void)buf;
    return (ssize_t)count;
}

struct bantu_driver bantu_null_driver = {
    .name   = "null",
    .type   = BANTU_DRV_CHAR,
    .minor  = 0,
    .status = 0,
    .init   = null_init,
    .shutdown = null_shutdown,
    .open   = NULL,
    .close  = NULL,
    .read   = null_read,
    .write  = null_write,
    .ioctl  = NULL,
    .private_data = NULL,
};

/* ---- ZERO device ---- */
static int zero_init(struct bantu_driver *drv) { (void)drv; return BANTU_DRV_OK; }

static ssize_t zero_read(struct bantu_driver *drv, void *buf, size_t count, long offset) {
    (void)drv; (void)offset;
    memset(buf, 0, count);
    return (ssize_t)count;
}

static ssize_t zero_write(struct bantu_driver *drv, const void *buf, size_t count, long offset) {
    (void)drv; (void)offset; (void)buf;
    return (ssize_t)count;
}

struct bantu_driver bantu_zero_driver = {
    .name   = "zero",
    .type   = BANTU_DRV_CHAR,
    .minor  = 1,
    .status = 0,
    .init   = zero_init,
    .shutdown = NULL,
    .open   = NULL,
    .close  = NULL,
    .read   = zero_read,
    .write  = zero_write,
    .ioctl  = NULL,
    .private_data = NULL,
};

/* ---- TTY driver ---- */
static char tty_input_buf[256];
static int tty_input_len = 0;
static pthread_mutex_t tty_lock = PTHREAD_MUTEX_INITIALIZER;

static int tty_init(struct bantu_driver *drv) {
    (void)drv;
    tty_input_len = 0;
    return BANTU_DRV_OK;
}

static ssize_t tty_read(struct bantu_driver *drv, void *buf, size_t count, long offset) {
    (void)drv; (void)offset;
    pthread_mutex_lock(&tty_lock);
    if (tty_input_len == 0) {
        pthread_mutex_unlock(&tty_lock);
        return 0;
    }
    size_t n = (size_t)tty_input_len < count ? (size_t)tty_input_len : count;
    memcpy(buf, tty_input_buf, n);
    tty_input_len = 0;
    pthread_mutex_unlock(&tty_lock);
    return (ssize_t)n;
}

static ssize_t tty_write(struct bantu_driver *drv, const void *buf, size_t count, long offset) {
    (void)drv; (void)offset;
    return (ssize_t)write(STDOUT_FILENO, buf, count);
}

struct bantu_driver bantu_tty_driver = {
    .name   = "tty",
    .type   = BANTU_DRV_CHAR,
    .minor  = 2,
    .status = 0,
    .init   = tty_init,
    .shutdown = NULL,
    .open   = NULL,
    .close  = NULL,
    .read   = tty_read,
    .write  = tty_write,
    .ioctl  = NULL,
    .private_data = NULL,
};